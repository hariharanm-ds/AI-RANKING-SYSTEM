import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

# Load .env relative to this file's directory — must run before ANY os.getenv call
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Default model fallback
_FALLBACK_MODEL = "llama-3.3-70b-versatile"

if not os.environ.get("GROQ_MODEL"):
    os.environ["GROQ_MODEL"] = _FALLBACK_MODEL


def _get_model() -> str:
    """Return the configured Groq model name."""
    return os.environ.get("GROQ_MODEL") or _FALLBACK_MODEL


def _get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return Groq(api_key=api_key)


def _extract_json(content: str) -> dict[str, Any]:
    """Parse JSON from model output, handling fenced code blocks."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Model response did not contain valid JSON.")


def parse_resume_with_groq(raw_text: str) -> dict[str, Any]:
    """Extract structured resume fields using Groq."""
    client = _get_client()
    prompt = f"""Extract structured information from this resume text.
Return ONLY valid JSON with these exact keys:
- name (string)
- skills (array of strings)
- experience (string summary)
- education (string summary)
- projects (string summary)
- certifications (string summary)

Resume:
{raw_text[:8000]}
"""

    response = client.chat.completions.create(
        model=_get_model(),
        messages=[
            {
                "role": "system",
                "content": "You are a resume parser. Return only valid JSON, no markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1500,
    )

    parsed = _extract_json(response.choices[0].message.content or "{}")
    parsed["raw_text"] = raw_text
    return parsed


def evaluate_candidate(job_description: str, resume_text: str) -> dict[str, Any]:
    """Compare a resume against a job description using Groq."""
    client = _get_client()
    prompt = f"""You are an expert recruiter. Compare this resume with the job description. Give:
- Match Score (0-100) as match_score
- Key Matching Skills as key_matching_skills (array of strings)
- Missing Skills as missing_skills (array of strings)
- Strengths as strengths (array of strings)
- Weaknesses as weaknesses (array of strings)
- Final Recommendation as recommendation (string)

Return ONLY valid JSON with keys:
match_score, key_matching_skills, missing_skills, strengths, weaknesses, recommendation

Job Description:
{job_description[:6000]}

Resume:
{resume_text[:8000]}
"""

    response = client.chat.completions.create(
        model=_get_model(),
        messages=[
            {
                "role": "system",
                "content": "You are an expert technical recruiter. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1200,
    )

    result = _extract_json(response.choices[0].message.content or "{}")
    match_score = result.get("match_score", 0)
    try:
        match_score = float(match_score)
    except (TypeError, ValueError):
        match_score = 0.0
    match_score = max(0.0, min(100.0, match_score))

    return {
        "match_score": match_score,
        "key_matching_skills": _as_list(result.get("key_matching_skills")),
        "missing_skills": _as_list(result.get("missing_skills")),
        "strengths": _as_list(result.get("strengths")),
        "weaknesses": _as_list(result.get("weaknesses")),
        "recommendation": str(result.get("recommendation", "No recommendation provided.")),
    }


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(value)]
