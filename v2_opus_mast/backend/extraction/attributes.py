import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

UNSPECIFIED = "unspecified"
SENIORITY_LEVELS = ["intern", "associate", "mid", "senior", "staff", "principal"]

# Checked in order: the first matching level wins (e.g. "Senior Staff" -> staff).
_SENIORITY_PATTERNS = [
    ("intern", r"\b(?:intern|interns|internship|co-?op)\b"),
    ("principal", r"\b(?:principal|distinguished)\b"),
    ("staff", r"\bstaff\b"),
    ("senior", r"\b(?:senior|sr)\b"),
    ("associate", r"\b(?:associate|junior|jr|entry[- ]level|new grad(?:uate)?|graduate)\b"),
    ("mid", r"\b(?:mid[- ]?level|mid|intermediate)\b"),
]

def parse_seniority(title: Optional[str]) -> str:
    """Maps a job title to a seniority level. Titles with no level signal stay 'unspecified'."""
    lower = (title or "").lower()
    for level, pattern in _SENIORITY_PATTERNS:
        if re.search(pattern, lower):
            return level
    return UNSPECIFIED


WORK_ARRANGEMENTS = ("remote", "hybrid", "onsite")

def parse_work_arrangement(explicit: Optional[str], location: Optional[str]) -> str:
    """
    Uses the provider's own workplace field when present, otherwise the location text.
    Returns remote | hybrid | onsite | unknown.
    """
    if explicit:
        compact = re.sub(r"[\s_\-]", "", str(explicit).lower())
        if "hybrid" in compact:
            return "hybrid"
        if "remote" in compact:
            return "remote"
        if compact in ("onsite", "inoffice", "office", "inperson"):
            return "onsite"

    lower = (location or "").lower()
    if re.search(r"\bhybrid\b", lower):
        return "hybrid"
    if re.search(r"\bremote\b", lower):
        return "remote"
    if re.search(r"\b(?:on-?site|in[- ]office|in[- ]person)\b", lower):
        return "onsite"
    return "unknown"


def parse_provider_timestamp(value: Any) -> Optional[datetime]:
    """Parses ISO-8601 strings, plain dates, and epoch seconds/milliseconds into UTC datetimes."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000.0 if value > 1e11 else float(value)
        try:
            dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Salary
# ---------------------------------------------------------------------------
CURRENCY_CODES = {
    "USD", "CAD", "AUD", "GBP", "EUR", "AED", "INR", "SGD", "CHF",
    "SEK", "DKK", "NOK", "PLN", "JPY", "NZD", "SAR", "QAR",
}
_SYMBOL_TO_CODE = {
    "US$": "USD", "CA$": "CAD", "C$": "CAD", "A$": "AUD",
    "$": "USD", "£": "GBP", "€": "EUR", "₹": "INR",
}
_CUR = r"(?:US\$|CA\$|C\$|A\$|\$|£|€|₹|\b(?:" + "|".join(sorted(CURRENCY_CODES)) + r")\b)"
_AMT = r"\d{1,3}(?:[,.\u00a0\u202f]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_RANGE_RE = re.compile(
    rf"(?P<c1>{_CUR})?\s*(?P<a>{_AMT})\s*(?P<ka>[kK]\b)?\s*(?P<c2>{_CUR})?"
    rf"\s*(?:-|–|—|to)\s*"
    rf"(?P<c3>{_CUR})?\s*(?P<b>{_AMT})\s*(?P<kb>[kK]\b)?\s*(?P<c4>{_CUR})?"
)
_SINGLE_RE = re.compile(
    rf"\b(?:salary|base pay|base salary|pay range|compensation)\b[^\n\d$£€₹]{{0,40}}"
    rf"(?P<c1>{_CUR})\s*(?P<a>{_AMT})\s*(?P<ka>[kK]\b)?\s*(?P<c2>{_CUR})?",
    re.IGNORECASE,
)
_NON_ANNUAL_RE = re.compile(
    r"\b(?:per\s+hour|an\s+hour|hourly|/\s*h(?:ou)?r|per\s+month|a\s+month|monthly|/\s*mo(?:nth)?|per\s+week|weekly|per\s+day|daily)\b",
    re.IGNORECASE,
)
_MIN_ANNUAL = 10_000
_MAX_ANNUAL = 10_000_000

def _to_number(raw: str, has_k: bool) -> Optional[float]:
    if re.fullmatch(r"\d{1,3}(?:[,.\u00a0\u202f]\d{3})+", raw):
        value = float(re.sub(r"\D", "", raw))
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+\.\d+", raw):
        value = float(raw.replace(",", ""))
    else:
        try:
            value = float(raw)
        except ValueError:
            return None
    return value * 1000 if has_k else value

def _currency_from(*tokens: Optional[str]) -> Optional[str]:
    present = [t for t in tokens if t]
    for token in present:
        if token.upper() in CURRENCY_CODES:
            return token.upper()
    for token in present:
        if token in _SYMBOL_TO_CODE:
            return _SYMBOL_TO_CODE[token]
    return None

def _is_non_annual(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 40): end + 40]
    return bool(_NON_ANNUAL_RE.search(window))

def _annual_interval(interval: Optional[str]) -> bool:
    if not interval:
        return False
    lower = str(interval).lower()
    return "year" in lower or "annual" in lower

def parse_salary(text: Optional[str], payload_salary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Returns {"salary_min", "salary_max", "salary_currency"} only when the posting states an
    annual salary with a currency. Hourly/monthly figures and bare numbers are ignored.
    """
    empty = {"salary_min": None, "salary_max": None, "salary_currency": None}

    if payload_salary and _annual_interval(payload_salary.get("interval")):
        currency = (payload_salary.get("currency") or "").upper() or None
        lo = payload_salary.get("min")
        hi = payload_salary.get("max")
        lo = float(lo) if isinstance(lo, (int, float)) and not isinstance(lo, bool) else None
        hi = float(hi) if isinstance(hi, (int, float)) and not isinstance(hi, bool) else None
        if currency in CURRENCY_CODES and (lo or hi):
            lo = lo if lo is not None else hi
            hi = hi if hi is not None else lo
            if _MIN_ANNUAL <= lo <= hi <= _MAX_ANNUAL:
                return {"salary_min": lo, "salary_max": hi, "salary_currency": currency}

    if not text:
        return empty

    for m in _RANGE_RE.finditer(text):
        currency = _currency_from(m.group("c1"), m.group("c2"), m.group("c3"), m.group("c4"))
        if not currency:
            continue
        kb = bool(m.group("kb"))
        hi = _to_number(m.group("b"), kb)
        lo_raw = _to_number(m.group("a"), False)
        # "$100-150k" shares the trailing k; "$90,000 - 120k" does not.
        lo_k = bool(m.group("ka")) or (kb and lo_raw is not None and lo_raw < 1000)
        lo = _to_number(m.group("a"), lo_k)
        if lo is None or hi is None or not (_MIN_ANNUAL <= lo <= hi <= _MAX_ANNUAL):
            continue
        if _is_non_annual(text, m.start(), m.end()):
            continue
        return {"salary_min": lo, "salary_max": hi, "salary_currency": currency}

    for m in _SINGLE_RE.finditer(text):
        currency = _currency_from(m.group("c1"), m.group("c2"))
        value = _to_number(m.group("a"), bool(m.group("ka")))
        if not currency or value is None or not (_MIN_ANNUAL <= value <= _MAX_ANNUAL):
            continue
        if _is_non_annual(text, m.start(), m.end()):
            continue
        return {"salary_min": value, "salary_max": value, "salary_currency": currency}

    return empty


# Pay bands compare the posting's own annual figure in its own currency (no FX conversion).
PAY_BANDS = {
    "under_100k": (None, 100_000),
    "100_150k": (100_000, 150_000),
    "150_200k": (150_000, 200_000),
    "200k_plus": (200_000, None),
}
PAY_UNKNOWN = "unknown"
