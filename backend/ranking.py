"""Candidate ranking logic combining semantic similarity and Groq evaluation."""

from typing import Any

from groq_client import evaluate_candidate


SEMANTIC_WEIGHT = 0.70
GROQ_WEIGHT = 0.30


def compute_final_score(similarity_score: float, match_score: float) -> float:
    """Combine normalized semantic similarity and Groq match score."""
    semantic_pct = max(0.0, min(1.0, similarity_score)) * 100.0
    groq_pct = max(0.0, min(100.0, match_score))
    return round((semantic_pct * SEMANTIC_WEIGHT) + (groq_pct * GROQ_WEIGHT), 2)


def rank_candidates(
    job_description: str,
    semantic_results: list[dict[str, Any]],
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Evaluate top semantic matches with Groq and produce final ranking."""
    candidates = semantic_results if top_n is None else semantic_results[:top_n]
    ranked: list[dict[str, Any]] = []

    for item in candidates:
        meta = item["metadata"]
        resume_text = meta.get("document_text") or item.get("document", "")

        try:
            evaluation = evaluate_candidate(job_description, resume_text)
        except Exception as exc:
            evaluation = {
                "match_score": 0.0,
                "key_matching_skills": [],
                "missing_skills": [],
                "strengths": [],
                "weaknesses": [f"Groq evaluation failed: {exc}"],
                "recommendation": "Unable to evaluate with Groq.",
            }

        similarity = float(item["similarity_score"])
        match_score = float(evaluation["match_score"])
        final_score = compute_final_score(similarity, match_score)

        ranked.append(
            {
                "candidate_name": meta.get("name", "Unknown"),
                "filename": meta.get("filename", ""),
                "similarity_score": round(similarity * 100, 2),
                "ai_match_score": round(match_score, 2),
                "final_score": final_score,
                "key_matching_skills": evaluation["key_matching_skills"],
                "missing_skills": evaluation["missing_skills"],
                "strengths": evaluation["strengths"],
                "weaknesses": evaluation["weaknesses"],
                "recommendation": evaluation["recommendation"],
                "parsed": meta.get("parsed", {}),
            }
        )

    ranked.sort(key=lambda row: row["final_score"], reverse=True)
    for rank, candidate in enumerate(ranked, start=1):
        candidate["rank"] = rank

    return ranked
