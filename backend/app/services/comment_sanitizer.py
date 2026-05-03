"""Sanitize free-text field comments before they reach a published UCMB report.

The platform stores assessor / manager / general comments verbatim — that is the right
behaviour at the operational layer. But when a comment is rendered into a DOCX or PDF
that goes to UCMB leadership, district health teams, and external stakeholders, we
must:

1. Drop comments that contain insults, profanity, or personal attacks.
2. Convert ALL-CAPS shouting to readable sentence case.
3. Trim and tidy whitespace.

This module keeps that policy in one place so both `report_data_service` (when building
the AI prompt input) and `export_service` (when rendering the field-notes section)
apply the same rules.
"""

from __future__ import annotations

import re

# Words that indicate a personal attack or unprofessional tone. Hit on any of these
# (whole-word match, case-insensitive) and the comment is withheld entirely.
_BLOCKLIST_WORDS = {
    # Insults / personal attacks
    "dumb", "stupid", "idiot", "idiots", "moron", "morons",
    "incompetent", "useless", "worthless", "pathetic", "lazy",
    "fool", "fools", "foolish",
    # Common profanity
    "fuck", "fucking", "shit", "bitch", "damn", "hell",
    "asshole", "bastard", "crap",
    # Slurs (extend as needed; minimal seed)
    "retard", "retarded",
}

_BLOCKLIST_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in _BLOCKLIST_WORDS) + r")\b",
    re.IGNORECASE,
)


def _is_shouting(text: str) -> bool:
    """A comment is considered 'shouting' if more than 60% of its alphabetic chars
    are uppercase AND the comment is at least 6 characters long."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 6:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) > 0.6


def _to_sentence_case(text: str) -> str:
    """Convert SHOUTING text to sentence-case prose. Preserves abbreviations that
    are commonly all-caps (HMIS, DHIS2, UCMB, ANC, PNC, IPD, etc.) by leaving
    short tokens of length <= 5 alone if they were originally all-caps."""
    preserve = {
        "HMIS", "DHIS2", "DHIS", "UCMB", "ANC", "PNC", "IPD", "OPD", "ART",
        "TB", "HIV", "STI", "EPI", "HC", "RHF", "MOH", "ID", "API", "URL",
        "JSON", "XML", "PDF", "DOCX", "XLSX", "CSV", "USD", "UGX", "WHO",
        "MNCH", "RMNCAH", "EmONC", "BEmONC", "CEmONC",
    }
    tokens = re.split(r"(\s+|[.,;:!?])", text)
    cleaned = []
    sentence_start = True
    for token in tokens:
        if not token or token.isspace() or token in {".", ",", ";", ":", "!", "?"}:
            cleaned.append(token)
            if token in {".", "!", "?"}:
                sentence_start = True
            continue
        upper_token = token.upper()
        if upper_token in preserve:
            cleaned.append(upper_token)
            sentence_start = False
            continue
        lowered = token.lower()
        if sentence_start:
            cleaned.append(lowered.capitalize())
            sentence_start = False
        else:
            cleaned.append(lowered)
    return "".join(cleaned).strip()


def sanitize_comment(text: str | None) -> str | None:
    """Return a cleaned comment safe for publication, or None if the comment should
    be omitted entirely.

    Returns None when:
    - text is None / empty / whitespace
    - text contains blocklisted insulting or profane content (whole-word match)

    Returns a cleaned string (possibly with sentence-cased shouting) otherwise.
    """
    if not text or not text.strip():
        return None
    cleaned = text.strip()
    if _BLOCKLIST_PATTERN.search(cleaned):
        return None
    if _is_shouting(cleaned):
        cleaned = _to_sentence_case(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None
    return cleaned


def sanitize_comment_or_paraphrase(text: str | None, *, paraphrase_template: str = "Field assessor noted concerns; specific wording withheld for professional tone.") -> str | None:
    """Like sanitize_comment, but instead of dropping a blocklisted comment entirely,
    return a neutral paraphrase. Useful when the section needs to acknowledge that
    SOMETHING was raised even if the wording can't be quoted.

    Returns None only if the input is empty.
    """
    if not text or not text.strip():
        return None
    cleaned = sanitize_comment(text)
    if cleaned is not None:
        return cleaned
    return paraphrase_template
