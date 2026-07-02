"""FastAPI application for AI Candidate Ranking System — NeuroRank AI."""
import os
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from embeddings import EmbeddingIndex
from groq_client import parse_resume_with_groq
from parser import (
    build_resume_document,
    clean_text,
    default_parsed_resume,
    extract_text_from_pdf,
    load_resume_json_records,
    parsed_resume_from_json,
)
from ranking import rank_candidates

# Load .env from the same directory as this file — works regardless of CWD
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Default model fallback
_FALLBACK_MODEL = "llama-3.3-70b-versatile"
if not os.environ.get("GROQ_MODEL"):
    os.environ["GROQ_MODEL"] = _FALLBACK_MODEL

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path("/tmp") if os.environ.get("VERCEL") else BASE_DIR
UPLOAD_DIR = RUNTIME_DIR / "uploads"
OUTPUT_DIR = RUNTIME_DIR / "output"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="NeuroRank AI — Candidate Ranking System",
    description="Rank candidates using semantic search (FAISS + SentenceTransformers) and Groq AI (Llama 3.3 70B) evaluation.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session state
state: dict[str, Any] = {
    "job_description": "",
    "job_filename": "",
    "resumes": [],
    "results": [],
    "embedding_index": None,
    "rank_status": "idle",  # idle | running | done | error
    "rank_progress": 0,
}


def _save_upload(upload: UploadFile, prefix: str) -> Path:
    suffix = Path(upload.filename or "file").suffix or ".pdf"
    file_id = uuid.uuid4().hex[:12]
    destination = UPLOAD_DIR / f"{prefix}_{file_id}{suffix}"
    content = upload.file.read()
    destination.write_bytes(content)
    return destination


# ─── Health ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, Any]:
    groq_key_set = bool(os.getenv("GROQ_API_KEY"))
    return {
        "status": "ok",
        "groq_api_key_configured": groq_key_set,
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "job_loaded": bool(state["job_description"]),
        "resume_count": len(state["resumes"]),
        "results_available": len(state["results"]) > 0,
    }


# ─── Upload Job Description ──────────────────────────────────────────────────
@app.post("/upload-job")
async def upload_job(
    job_text: str | None = Form(default=None),
    job_file: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    """Upload job description as text and/or PDF."""
    if not job_text and not job_file:
        raise HTTPException(status_code=400, detail="Provide job description text or PDF.")

    parts: list[str] = []

    if job_text and job_text.strip():
        parts.append(clean_text(job_text))

    saved_name = ""
    if job_file and job_file.filename:
        if not job_file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Job file must be a PDF.")
        path = _save_upload(job_file, "job")
        saved_name = path.name
        parts.append(clean_text(extract_text_from_pdf(path)))

    job_description = clean_text("\n\n".join(parts))
    if not job_description:
        raise HTTPException(status_code=400, detail="Job description is empty after processing.")

    state["job_description"] = job_description
    state["job_filename"] = saved_name
    state["results"] = []
    state["embedding_index"] = None
    state["rank_status"] = "idle"
    state["rank_progress"] = 0

    return {
        "message": "Job description uploaded successfully.",
        "length": len(job_description),
        "filename": saved_name or None,
        "preview": job_description[:300] + ("..." if len(job_description) > 300 else ""),
    }


# ─── Upload Resumes ───────────────────────────────────────────────────────────
@app.post("/upload-resumes")
async def upload_resumes(resume_files: list[UploadFile] = File(...)) -> dict[str, Any]:
    """Upload multiple resume PDFs or JSON files, then parse candidates."""
    if not resume_files:
        raise HTTPException(status_code=400, detail="At least one resume PDF or JSON file is required.")

    resumes: list[dict[str, Any]] = []
    parse_errors: list[str] = []

    for upload in resume_files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".json"}:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file: {filename}. Only PDF and JSON files are allowed.",
            )

        path = _save_upload(upload, "resume")
        if suffix == ".json":
            try:
                records = load_resume_json_records(path)
            except ValueError as e:
                parse_errors.append(str(e))
                continue

            for index, record in enumerate(records, start=1):
                parsed = parsed_resume_from_json(record, filename)
                document_text = build_resume_document(parsed)
                candidate_filename = filename if len(records) == 1 else f"{filename}#{index}"
                resumes.append(
                    {
                        "filename": candidate_filename,
                        "saved_path": str(path),
                        "parsed": parsed,
                        "document_text": document_text,
                        "name": parsed.get("name") or Path(filename).stem,
                    }
                )
            continue

        try:
            raw_text = clean_text(extract_text_from_pdf(path))
        except ValueError as e:
            parse_errors.append(str(e))
            continue

        try:
            parsed = parse_resume_with_groq(raw_text)
        except Exception as exc:
            parse_errors.append(f"{filename}: Groq parse failed — {exc}")
            parsed = default_parsed_resume(filename, raw_text)

        document_text = build_resume_document(parsed) or raw_text
        resumes.append(
            {
                "filename": filename,
                "saved_path": str(path),
                "parsed": parsed,
                "document_text": document_text,
                "name": parsed.get("name") or Path(filename).stem,
            }
        )

    if not resumes:
        raise HTTPException(
            status_code=422,
            detail=f"No resumes could be processed. Errors: {'; '.join(parse_errors)}",
        )

    state["resumes"] = resumes
    state["results"] = []
    state["embedding_index"] = None
    state["rank_status"] = "idle"

    return {
        "message": f"{len(resumes)} resume(s) uploaded and parsed successfully.",
        "count": len(resumes),
        "candidates": [{"filename": r["filename"], "name": r["name"]} for r in resumes],
        "parse_errors": parse_errors,
    }


# ─── Rank Candidates ──────────────────────────────────────────────────────────
@app.post("/rank")
async def rank() -> dict[str, Any]:
    """Run semantic embedding search + Groq AI evaluation to rank all candidates."""
    if not state["job_description"]:
        raise HTTPException(status_code=400, detail="Upload a job description first (Step 1).")
    if not state["resumes"]:
        raise HTTPException(status_code=400, detail="Upload at least one resume first (Step 2).")

    state["rank_status"] = "running"
    state["rank_progress"] = 0

    try:
        documents = [r["document_text"] for r in state["resumes"]]
        metadata = [
            {
                "filename": r["filename"],
                "name": r["name"],
                "parsed": r["parsed"],
                "document_text": r["document_text"],
            }
            for r in state["resumes"]
        ]

        state["rank_progress"] = 20
        index = EmbeddingIndex()
        index.build(documents, metadata)
        state["embedding_index"] = index

        state["rank_progress"] = 50
        semantic_results = index.search(state["job_description"], top_k=len(documents))

        state["rank_progress"] = 70
        ranked = rank_candidates(state["job_description"], semantic_results)
        state["results"] = ranked
        state["rank_progress"] = 90

        csv_path = OUTPUT_DIR / "ranked_candidates.csv"
        _write_results_csv(ranked, csv_path)
        state["rank_progress"] = 100
        state["rank_status"] = "done"

        return {
            "message": "Ranking completed successfully.",
            "total_candidates": len(ranked),
            "results": ranked,
        }

    except Exception as exc:
        state["rank_status"] = "error"
        raise HTTPException(status_code=500, detail=f"Ranking failed: {str(exc)}") from exc


# ─── Get Results ───────────────────────────────────────────────────────────────
@app.get("/results")
async def get_results() -> dict[str, Any]:
    """Return the latest ranking results."""
    return {
        "total": len(state["results"]),
        "results": state["results"],
        "job_description_loaded": bool(state["job_description"]),
        "resume_count": len(state["resumes"]),
        "rank_status": state["rank_status"],
        "rank_progress": state["rank_progress"],
    }


# ─── Download CSV ──────────────────────────────────────────────────────────────
@app.get("/download-csv")
async def download_csv() -> FileResponse:
    """Download ranked candidates as CSV."""
    if not state["results"]:
        raise HTTPException(status_code=404, detail="No results available. Run /rank first.")

    csv_path = OUTPUT_DIR / "ranked_candidates.csv"
    _write_results_csv(state["results"], csv_path)
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="neurorank_results.csv",
    )


# ─── Reset Session ────────────────────────────────────────────────────────────
@app.post("/reset")
async def reset_session() -> dict[str, str]:
    """Clear all session state."""
    state["job_description"] = ""
    state["job_filename"] = ""
    state["resumes"] = []
    state["results"] = []
    state["embedding_index"] = None
    state["rank_status"] = "idle"
    state["rank_progress"] = 0
    return {"message": "Session reset successfully."}


# ─── CSV Writer ────────────────────────────────────────────────────────────────
def _write_results_csv(results: list[dict[str, Any]], path: Path) -> None:
    rows = []
    for item in results:
        rows.append(
            {
                "Rank": item.get("rank"),
                "Candidate Name": item.get("candidate_name"),
                "Filename": item.get("filename"),
                "Similarity Score (%)": item.get("similarity_score"),
                "AI Match Score": item.get("ai_match_score"),
                "Final Score": item.get("final_score"),
                "Key Matching Skills": "; ".join(item.get("key_matching_skills", [])),
                "Missing Skills": "; ".join(item.get("missing_skills", [])),
                "Strengths": "; ".join(item.get("strengths", [])),
                "Weaknesses": "; ".join(item.get("weaknesses", [])),
                "Recommendation": item.get("recommendation"),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8")


# ─── Serve Frontend ────────────────────────────────────────────────────────────
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_frontend() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")
