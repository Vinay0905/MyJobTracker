import re
from typing import List, Dict, Any, Optional

def extract_experience_requirements(text: str) -> List[Dict[str, Any]]:
    """
    Extracts distinct experience requirements, years ranges, scopes, and supporting evidence text.
    """
    results: List[Dict[str, Any]] = []
    lines = text.split("\n")

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue

        lower_line = cleaned_line.lower()

        # 1. Entry level signal check
        if re.search(r"\b(?:new grad(?:uates?)?|recent graduates?|entry[- ]level|internship)\b", lower_line):
            results.append({
                "min_years": 0,
                "max_years": 1,
                "experience_scope": "entry_level_signal",
                "related_skill": None,
                "evidence_text": cleaned_line,
            })
            continue

        # 2. Degree equivalent check (e.g. "Bachelor's degree or 4 years equivalent practical experience")
        deg_match = re.search(r"or\s+(\d+)\+?\s*years?\s+(?:of\s+)?(?:equivalent|practical)", lower_line)
        if deg_match:
            results.append({
                "min_years": int(deg_match.group(1)),
                "max_years": None,
                "experience_scope": "degree_equivalent",
                "related_skill": None,
                "evidence_text": cleaned_line,
            })
            continue

        # 3. Standard YOE check: range (e.g. "3-5 years") or single (e.g. "5+ years")
        range_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\+?\s*years?", lower_line)
        single_match = re.search(r"(\d+)\+?\s*years?", lower_line)

        min_y = None
        max_y = None

        if range_match:
            min_y = int(range_match.group(1))
            max_y = int(range_match.group(2))
        elif single_match:
            min_y = int(single_match.group(1))
            max_y = None

        if min_y is not None:
            # Determine whether it is overall professional or skill specific
            is_skill_specific = False
            related_skill_name = None

            for known in ["c++", "cuda", "python", "unreal", "unity", "docker", "kubernetes", "vulkan", "rtos", "rust", "go"]:
                if known in lower_line:
                    is_skill_specific = True
                    related_skill_name = known.upper()
                    break

            scope = "skill_specific" if is_skill_specific else "overall_professional"

            results.append({
                "min_years": min_y,
                "max_years": max_y,
                "experience_scope": scope,
                "related_skill": related_skill_name,
                "evidence_text": cleaned_line,
            })

    return results
