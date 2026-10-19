import hashlib
import re
from typing import Dict, List, Tuple
try:
    from selectolax.lexbor import LexborHTMLParser as HTMLParser
except ImportError:
    from selectolax.parser import HTMLParser

SECTION_PATTERNS = {
    "REQUIRED_SECTION": [
        r"what (?:you'll|you will) need",
        r"basic qualifications",
        r"minimum qualifications",
        r"minimum requirements",
        r"required skills",
        r"what we're looking for",
        r"must have",
        r"requirements",
        r"qualifications",
    ],
    "PREFERRED_SECTION": [
        r"preferred qualifications",
        r"bonus points",
        r"nice to have",
        r"preferred skills",
        r"desirable",
        r"extra points",
        r"what would give you an edge",
        r"stand out",
    ],
    "RESPONSIBILITIES_SECTION": [
        r"what (?:you'll|you will) do",
        r"responsibilities",
        r"key duties",
        r"the role",
        r"about the job",
    ],
    "COMPANY_BOILERPLATE": [
        r"about nvidia",
        r"about epic games",
        r"about careem",
        r"about us",
        r"who we are",
        r"equal opportunity",
        r"diversity and inclusion",
        r"benefits",
        r"perks",
        r"privacy policy",
    ],
}

def clean_html_to_text(raw_html: str) -> str:
    """Strips tags, scripts, and styles while preserving clean line breaks and list structure."""
    if not raw_html:
        return ""
    
    # Strip dangerous/unnecessary tags
    tree = HTMLParser(raw_html)
    for tag in tree.css("script, style, link, meta, noscript"):
        tag.decompose()

    text = tree.text(separator="\n")
    # Normalize whitespace while preserving line structure
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join([line for line in lines if line])
    return cleaned

def compute_description_hash(normalized_text: str) -> str:
    """Computes a stable SHA-256 fingerprint of the normalized text."""
    # Collapse multiple newlines into single spaces for hash stability
    canonical = re.sub(r"\s+", " ", normalized_text).strip().lower()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def segment_description(text: str) -> Dict[str, List[str]]:
    """Segments cleaned description text into semantically labeled blocks."""
    lines = text.split("\n")
    sections: Dict[str, List[str]] = {
        "REQUIRED_SECTION": [],
        "PREFERRED_SECTION": [],
        "RESPONSIBILITIES_SECTION": [],
        "COMPANY_BOILERPLATE": [],
        "GENERAL_SECTION": [],
    }

    current_section = "GENERAL_SECTION"

    for line in lines:
        stripped = line.strip()
        lower_line = stripped.lower()

        matched_section = None
        for sec_name, patterns in SECTION_PATTERNS.items():
            for pat in patterns:
                # Match heading lines (stand-alone title line or short line ending in colon)
                if re.search(rf"^(?:[\#\*\-•\s]*){pat}[:\s]*$", lower_line) or (
                    stripped.endswith(":") and len(stripped) < 40 and re.search(rf"\b{pat}\b", lower_line)
                ):
                    matched_section = sec_name
                    break
            if matched_section:
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(stripped)

    return sections
