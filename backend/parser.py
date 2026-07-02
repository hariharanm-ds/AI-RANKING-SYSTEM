"""Resume and job description parsing utilities."""

import re
from pathlib import Path
from typing import Any

import pdfplumber
from PyPDF2 import PdfReader


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract text from a PDF using pdfplumber with PyPDF2 fallback."""
    path = Path(file_path)
    text_parts: list[str] = []

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())
    except Exception:
        pass

    if text_parts:
        return "\n\n".join(text_parts)

    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    except Exception as exc:
        raise ValueError(f"Failed to extract text from PDF: {path.name}") from exc

    if not text_parts:
        raise ValueError(f"No text could be extracted from PDF: {path.name}")

    return "\n\n".join(text_parts)


def clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_resume_document(parsed: dict[str, Any]) -> str:
    """Build a searchable text document from structured resume fields."""
    sections = [
        ("Name", parsed.get("name", "")),
        ("Skills", ", ".join(parsed.get("skills", []))),
        ("Experience", parsed.get("experience", "")),
        ("Education", parsed.get("education", "")),
        ("Projects", parsed.get("projects", "")),
        ("Certifications", parsed.get("certifications", "")),
    ]
    return "\n".join(f"{label}: {value}" for label, value in sections if value)


def default_parsed_resume(filename: str, raw_text: str) -> dict[str, Any]:
    """Fallback structured resume when Groq parsing is unavailable."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    name = lines[0][:120] if lines else Path(filename).stem.replace("_", " ")

    return {
        "name": name,
        "skills": [],
        "experience": raw_text[:3000],
        "education": "",
        "projects": "",
        "certifications": "",
        "raw_text": raw_text,
    }
