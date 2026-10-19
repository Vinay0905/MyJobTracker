from typing import Dict, Any, List, Optional
from backend.extraction.normalizer import clean_html_to_text, compute_description_hash, segment_description
from backend.extraction.filter import is_engineering_role
from backend.extraction.taxonomy import extract_skills_with_evidence
from backend.extraction.experience import extract_experience_requirements, governing_min_years

def process_job_description(
    title: str,
    department: str,
    raw_html_or_text: str,
) -> Dict[str, Any]:
    """
    Runs the complete normalization, filtering, taxonomy extraction, and experience parsing pipeline.
    """
    normalized_text = clean_html_to_text(raw_html_or_text)
    desc_hash = compute_description_hash(normalized_text)

    is_valid, reason = is_engineering_role(title, department, normalized_text)
    if not is_valid:
        return {
            "is_engineering": False,
            "rejection_reason": reason,
            "normalized_description": normalized_text,
            "description_hash": desc_hash,
            "skills": [],
            "experience": [],
        }

    sections = segment_description(normalized_text)
    skills = extract_skills_with_evidence(sections)
    experience = extract_experience_requirements(normalized_text)

    return {
        "is_engineering": True,
        "rejection_reason": None,
        "normalized_description": normalized_text,
        "description_hash": desc_hash,
        "sections": {k: len(v) for k, v in sections.items()},
        "skills": skills,
        "experience": experience,
        "primary_min_yoe": governing_min_years(experience),
    }
