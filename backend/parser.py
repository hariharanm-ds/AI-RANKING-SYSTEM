"""Resume and job description parsing utilities."""

import json
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


def load_resume_json_records(file_path: str | Path) -> list[dict[str, Any]]:
    """Load one or more candidate records from a JSON resume file."""
    path = Path(file_path)

    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8")

    records = _parse_json_candidate_records(content)
    if not records:
        raise ValueError(f"No candidate records found in JSON: {path.name}")

    return records


def parsed_resume_from_json(record: dict[str, Any], filename: str) -> dict[str, Any]:
    """Normalize a JSON candidate profile into the app's parsed resume shape."""
    profile = _dict_value(record.get("profile"))
    candidate_id = _string_value(record.get("candidate_id") or record.get("id"))

    name = _first_text(
        profile.get("anonymized_name"),
        profile.get("name"),
        record.get("name"),
        record.get("candidate_name"),
        candidate_id,
        Path(filename).stem.replace("_", " "),
    )

    skills = _skill_names(record.get("skills") or profile.get("skills"))

    career_history = _list_of_dicts(
        record.get("career_history")
        or record.get("experience")
        or record.get("work_experience")
        or profile.get("career_history")
    )
    experience_text = ""
    if isinstance(record.get("experience"), str):
        experience_text = _string_value(record.get("experience"))
    elif isinstance(profile.get("experience"), str):
        experience_text = _string_value(profile.get("experience"))

    experience_parts = [
        _labeled("Candidate ID", candidate_id),
        _labeled("Headline", _string_value(profile.get("headline") or record.get("headline"))),
        _labeled("Summary", _string_value(profile.get("summary") or record.get("summary"))),
        _labeled("Location", _location_text(profile)),
        _labeled("Years of Experience", _string_value(profile.get("years_of_experience") or record.get("years_of_experience"))),
        _labeled("Current Role", _current_role_text(profile)),
        _labeled("Experience", experience_text),
        _history_text(career_history),
    ]

    education = _education_text(record.get("education") or profile.get("education"))
    projects = _generic_section_text(record.get("projects") or profile.get("projects"))
    certifications = _certification_text(record.get("certifications") or profile.get("certifications"))
    raw_text = _json_record_text(record, filename)

    return {
        "name": name,
        "skills": skills,
        "experience": clean_text("\n".join(part for part in experience_parts if part)),
        "education": education,
        "projects": projects,
        "certifications": certifications,
        "raw_text": raw_text,
        "candidate_id": candidate_id,
        "source_type": "json",
    }


def build_resume_document(parsed: dict[str, Any]) -> str:
    """Build a searchable text document from structured resume fields."""
    sections = [
        ("Name", parsed.get("name", "")),
        ("Skills", ", ".join(_string_value(skill) for skill in parsed.get("skills", []) if _string_value(skill))),
        ("Experience", parsed.get("experience", "")),
        ("Education", parsed.get("education", "")),
        ("Projects", parsed.get("projects", "")),
        ("Certifications", parsed.get("certifications", "")),
    ]
    if parsed.get("source_type") == "json":
        sections.append(("Raw Profile", parsed.get("raw_text", "")))
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


def _parse_json_candidate_records(content: str) -> list[dict[str, Any]]:
    content = content.strip()
    if not content:
        return []

    try:
        return _extract_candidate_records(json.loads(content))
    except json.JSONDecodeError:
        pass

    records: list[dict[str, Any]] = []
    for line in content.splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped:
            continue
        candidates = [stripped]
        if stripped.startswith('"'):
            candidates.append("{" + stripped)
        for candidate in candidates:
            try:
                records.extend(_extract_candidate_records(json.loads(candidate)))
                break
            except json.JSONDecodeError:
                continue

    if records:
        return records

    decoder = json.JSONDecoder()
    index = 0
    while index < len(content):
        while index < len(content) and content[index] in " \t\r\n,":
            index += 1
        if index >= len(content):
            break
        try:
            value, end = decoder.raw_decode(content, index)
        except json.JSONDecodeError:
            break
        records.extend(_extract_candidate_records(value))
        index = end

    return records


def _extract_candidate_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if isinstance(value, dict):
        for key in ("candidates", "resumes", "profiles", "records", "items", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]

    return []


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, (int, float, bool)):
        return str(value)
    return clean_text(json.dumps(value, ensure_ascii=False))


def _first_text(*values: Any) -> str:
    for value in values:
        text = _string_value(value)
        if text:
            return text
    return "Unknown Candidate"


def _first_optional_text(*values: Any) -> str:
    for value in values:
        text = _string_value(value)
        if text:
            return text
    return ""


def _labeled(label: str, value: str) -> str:
    return f"{label}: {value}" if value else ""


def _location_text(profile: dict[str, Any]) -> str:
    return ", ".join(
        part
        for part in (
            _string_value(profile.get("location")),
            _string_value(profile.get("country")),
        )
        if part
    )


def _current_role_text(profile: dict[str, Any]) -> str:
    title = _string_value(profile.get("current_title"))
    company = _string_value(profile.get("current_company"))
    industry = _string_value(profile.get("current_industry"))
    role = " at ".join(part for part in (title, company) if part)
    if industry:
        role = f"{role} ({industry})" if role else industry
    return role


def _skill_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = _first_optional_text(item.get("name"), item.get("skill"), item.get("title"))
            proficiency = _string_value(item.get("proficiency"))
            duration = _string_value(item.get("duration_months"))
            if name and (proficiency or duration):
                extras = ", ".join(
                    part
                    for part in (
                        proficiency,
                        f"{duration} months" if duration else "",
                    )
                    if part
                )
                names.append(f"{name} ({extras})")
            elif name:
                names.append(name)
        else:
            text = _string_value(item)
            if text:
                names.append(text)

    return names


def _history_text(records: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in records:
        title = _string_value(item.get("title"))
        company = _string_value(item.get("company"))
        start = _string_value(item.get("start_date"))
        end = _string_value(item.get("end_date")) or "present"
        description = _string_value(item.get("description"))
        duration = _string_value(item.get("duration_months"))

        heading = " - ".join(part for part in (title, company) if part)
        dates = f"{start} to {end}" if start or end != "present" else ""
        if duration:
            dates = f"{dates}; {duration} months" if dates else f"{duration} months"

        detail = ". ".join(part for part in (heading, dates, description) if part)
        if detail:
            parts.append(detail)

    return "Career History:\n" + "\n".join(f"- {part}" for part in parts) if parts else ""


def _education_text(value: Any) -> str:
    if isinstance(value, str):
        return clean_text(value)

    entries = _list_of_dicts(value)
    parts: list[str] = []
    for item in entries:
        degree = _string_value(item.get("degree"))
        field = _string_value(item.get("field_of_study") or item.get("field"))
        institution = _string_value(item.get("institution") or item.get("school"))
        start = _string_value(item.get("start_year"))
        end = _string_value(item.get("end_year"))
        grade = _string_value(item.get("grade"))

        credential = " ".join(part for part in (degree, field) if part)
        years = "-".join(part for part in (start, end) if part)
        detail = ", ".join(part for part in (credential, institution, years, grade) if part)
        if detail:
            parts.append(detail)

    return "\n".join(f"- {part}" for part in parts)


def _certification_text(value: Any) -> str:
    if isinstance(value, str):
        return clean_text(value)
    if not isinstance(value, list):
        return ""

    parts: list[str] = []
    for item in value:
        if isinstance(item, dict):
            parts.append(
                ", ".join(
                    part
                    for part in (
                        _first_optional_text(item.get("name"), item.get("title"), item.get("certification")),
                        _string_value(item.get("issuer")),
                        _string_value(item.get("year") or item.get("date")),
                    )
                    if part
                )
            )
        else:
            parts.append(_string_value(item))

    return "\n".join(f"- {part}" for part in parts if part)


def _generic_section_text(value: Any) -> str:
    if isinstance(value, str):
        return clean_text(value)
    if not value:
        return ""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(
                    ", ".join(
                        part
                        for part in (
                            _first_optional_text(item.get("name"), item.get("title")),
                            _string_value(item.get("description")),
                        )
                        if part
                    )
                )
            else:
                parts.append(_string_value(item))
        return "\n".join(f"- {part}" for part in parts if part)
    return _string_value(value)


def _json_record_text(record: dict[str, Any], filename: str) -> str:
    pretty = json.dumps(record, ensure_ascii=False, indent=2)
    return clean_text(f"Source file: {filename}\n{pretty}")
