import re
from typing import Tuple

INCLUDE_KEYWORDS = [
    r"\bengineer(?:ing)?\b", r"\bdeveloper\b", r"\bprogrammer\b",
    r"\barchitect\b", r"\bdevops\b", r"\bsre\b", r"\bdeployment\b",
    r"\binfrastructure\b", r"\bcloud\b", r"\bbackend\b", r"\bfrontend\b",
    r"\bfullstack\b", r"\bfull-stack\b", r"\bsystems?\b", r"\bembedded\b",
    r"\bfirmware\b", r"\bkernel\b", r"\bgpu\b", r"\bcuda\b", r"\bgraphics\b",
    r"\brendering\b", r"\bai\b", r"\bmachine learning\b", r"\bml\b",
    r"\bdeep learning\b", r"\bdata scientist\b", r"\bdata engineer\b",
    r"\bnlp\b", r"\bcomputer vision\b", r"\brobotics\b", r"\bsecurity\b",
    r"\bnetwork(?:ing)?\b", r"\bgameplay\b", r"\bengine\b",
    r"\btools programmer\b", r"\bcompiler\b", r"\bruntime\b",
    r"\brtos\b", r"\bqa automation\b", r"\bsdet\b", r"\bresearch scientist\b"
]

EXCLUDE_KEYWORDS = [
    r"\bhr\b", r"\bhuman resources\b", r"\brecruiter\b", r"\btalent acquisition\b",
    r"\bpeople partner\b", r"\bpayroll\b", r"\bfinance\b", r"\baccounting\b",
    r"\baccountant\b", r"\btreasury\b", r"\btax\b", r"\baudit\b",
    r"\bsales\b", r"\bbusiness development\b", r"\baccount executive\b",
    r"\baccount manager\b", r"\boperations lead\b", r"\boperations manager\b",
    r"\bmarketing\b", r"\bseo\b", r"\bcontent writer\b", r"\bcopywriter\b",
    r"\blegal\b", r"\bcounsel\b", r"\bparalegal\b", r"\bcompliance officer\b",
    r"\bartist\b", r"\billustrator\b", r"\banimator\b", r"\bconcept art\b",
    r"\bcharacter art\b", r"\benvironment art\b", r"\blighting artist\b",
    r"\b3d artist\b", r"\b2d artist\b", r"\bsound designer\b", r"\baudio designer\b",
    r"\bcomposer\b", r"\bvoice actor\b", r"\bnarrative\b", r"\bpr\b",
    r"\bpublic relations\b", r"\bcommunications\b", r"\boffice manager\b",
    r"\bexecutive assistant\b", r"\bfacilities\b", r"\bcatering\b",
    r"\boperations coordinator\b", r"\bevents? coordinator\b", r"\bdriver operations\b"
]

STRONG_TECH_REQUIREMENTS = [
    r"\b(?:c\+\+|python|rust|golang|java|cuda|embedded\s+c|kernel\s+development|software\s+development)\b"
]

def is_engineering_role(title: str, department: str = "", description: str = "") -> Tuple[bool, str]:
    """
    Evaluates whether a job posting strictly belongs to software/AI/systems engineering.
    Returns (is_valid, reason).
    """
    combined_header = f"{title} {department}".lower()

    # 1. Immediate rejection of excluded roles
    for pat in EXCLUDE_KEYWORDS:
        if re.search(pat, combined_header):
            # Special check for technical artist / shader developer (only accept if C++ Engine Core, Physics, GPU Compute, or AI tools focused)
            if "technical artist" in combined_header or "tech art" in combined_header or "shader" in combined_header:
                lower_desc = description.lower()
                has_core_eng = any(k in lower_desc for k in ["c++", "physics", "cuda", "gpu compute", "tool development", "engine core"])
                if has_core_eng:
                    return True, "Technical Artist / Shader Developer with confirmed C++/Engine/GPU scope"
            return False, f"Rejected: matched excluded keyword {pat}"

    # 2. Check for inclusion in Title/Department
    has_include = any(re.search(pat, combined_header) for pat in INCLUDE_KEYWORDS)
    if has_include:
        return True, "Accepted: matched engineering keyword in header"

    # 3. Fallback: Only accept if description demonstrates strong programming/software development requirements
    lower_desc = description.lower()
    if any(re.search(pat, lower_desc) for pat in STRONG_TECH_REQUIREMENTS):
        if any(term in lower_desc for term in ["responsibilities", "requirements", "qualifications"]):
            return True, "Accepted: confirmed software/programming scope in requirements"

    return False, "Rejected: no engineering keyword found in title, department or header"
