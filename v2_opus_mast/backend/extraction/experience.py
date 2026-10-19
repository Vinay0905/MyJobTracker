import re
from typing import List, Dict, Any, Optional, Iterable, Tuple

_YEARS_RE = re.compile(
    r"(?P<min>\d{1,2})\s*(?P<plus1>\+)?\s*(?:(?:-|–|—|to)\s*(?P<max>\d{1,2})\s*(?P<plus2>\+)?\s*)?years?\b",
    re.IGNORECASE,
)
_AGE_AFTER_RE = re.compile(r"^\s*(?:of\s+age|old\b|or\s+older|and\s+(?:older|above|over))", re.IGNORECASE)
_AGE_BEFORE_RE = re.compile(r"\bage(?:d)?\s*(?:of\s*)?$", re.IGNORECASE)
_HISTORY_BEFORE_RE = re.compile(
    r"\b(?:for|over|than|since|nearly|almost|spanning|past|last|celebrating)\s*(?:(?:over|more\s+than|nearly|almost|the\s+past|the\s+last)\s*)?$",
    re.IGNORECASE,
)
_EXPERIENCE_AFTER_RE = re.compile(
    r"^\s*(?:of\s+)?(?:[\w/+#.&,'’-]+\s+){0,7}?(?:experience|expertise)\b",
    re.IGNORECASE,
)
_WORK_AFTER_RE = re.compile(
    r"^\s*(?:of\s+)?(?:professional|industry|relevant|hands-on|practical|working|work|commercial|"
    r"programming|development|engineering|software|post-graduate|postgraduate|"
    r"developing|building|writing|designing|shipping|leading|delivering|"
    r"in\s+(?:the\s+|a\s+|an\s+)?(?:[\w/+#.-]+\s+){0,3}?(?:industry|development|engineering|role|position|field|games?))\b",
    re.IGNORECASE,
)
_REQUIREMENT_BEFORE_RE = re.compile(
    r"\b(?:minimum|min\.?|at\s+least|requires?|required|must\s+have)\s*(?:of\s*)?$",
    re.IGNORECASE,
)

def requirement_years_in_line(line: str) -> List[Tuple[int, Optional[int]]]:
    """
    Returns (min_years, max_years) pairs that read as an experience requirement.
    Skips age limits ("18 years or older") and company history ("for over 30 years").
    """
    found: List[Tuple[int, Optional[int]]] = []
    for m in _YEARS_RE.finditer(line):
        before = line[max(0, m.start() - 40): m.start()]
        after = line[m.end(): m.end() + 90]

        if _AGE_AFTER_RE.search(after) or _AGE_BEFORE_RE.search(before):
            continue

        tied_to_experience = bool(_EXPERIENCE_AFTER_RE.search(after) or _WORK_AFTER_RE.search(after))
        if _HISTORY_BEFORE_RE.search(before) and not tied_to_experience:
            continue

        has_plus = bool(m.group("plus1") or m.group("plus2"))
        if not (tied_to_experience or has_plus or _REQUIREMENT_BEFORE_RE.search(before)):
            continue

        min_y = int(m.group("min"))
        max_y = int(m.group("max")) if m.group("max") else None
        if min_y > 25 or (max_y is not None and max_y < min_y):
            continue
        found.append((min_y, max_y))
    return found

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

        # 3. Standard YOE check, only on lines where the years read as an experience requirement
        year_pairs = requirement_years_in_line(cleaned_line)
        if not year_pairs:
            continue
        min_y, max_y = year_pairs[0]

        is_skill_specific = False
        related_skill_name = None

        for known in ["c++", "cuda", "python", "unreal", "unity", "docker", "kubernetes", "vulkan", "rtos", "rust", "go"]:
            if re.search(rf"(?<![a-z0-9]){re.escape(known)}(?![a-z0-9+#])", lower_line):
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


_GOVERNING_TIERS = (
    ("overall_professional", "role_specific"),
    ("skill_specific", "domain_specific"),
    ("entry_level_signal",),
)

def _field(req: Any, key: str) -> Any:
    return req.get(key) if isinstance(req, dict) else getattr(req, key, None)

def governing_requirement(requirements: Iterable[Any]) -> Optional[Any]:
    """
    Picks the requirement that sets a job's minimum years. Accepts extraction dicts or
    JobExperienceRequirement rows. Overall experience wins over skill-specific lines, and
    degree-equivalent alternatives never set the minimum. Stored rows whose evidence does not
    read as an experience requirement (age limits, company history) are ignored.
    """
    usable = []
    for req in requirements or []:
        if _field(req, "min_years") is None:
            continue
        scope = _field(req, "experience_scope")
        if scope == "degree_equivalent":
            continue
        if scope != "entry_level_signal" and not requirement_years_in_line(_field(req, "evidence_text") or ""):
            continue
        usable.append(req)

    for tier in _GOVERNING_TIERS:
        candidates = [r for r in usable if _field(r, "experience_scope") in tier]
        if candidates:
            return max(candidates, key=lambda r: _field(r, "min_years"))
    return None

def governing_min_years(requirements: Iterable[Any]) -> Optional[int]:
    """The single years number shown on the job card, used by the years filter and the gap analyzer."""
    req = governing_requirement(requirements)
    return _field(req, "min_years") if req is not None else None
