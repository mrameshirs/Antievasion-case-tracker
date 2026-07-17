# validators.py
import re
from config import GSTIN_REGEX, INVESTIGATION_GROUPS

_gstin_pattern = re.compile(GSTIN_REGEX)


def split_list_field(raw_text):
    """Splits a comma/semicolon separated string into a clean list of items."""
    if not raw_text:
        return []
    parts = re.split(r'[;,]', raw_text)
    return [p.strip() for p in parts if p.strip()]


def validate_gstins(raw_text_or_list):
    """
    Validates a comma/semicolon separated string (or list) of GSTINs against
    the standard 15-character GSTIN pattern.
    Returns (valid_gstins: list, invalid_gstins: list).
    """
    if isinstance(raw_text_or_list, str):
        candidates = split_list_field(raw_text_or_list)
    else:
        candidates = [str(g).strip() for g in (raw_text_or_list or []) if str(g).strip()]

    valid, invalid = [], []
    for g in candidates:
        g_clean = g.upper().replace(" ", "")
        if _gstin_pattern.match(g_clean):
            valid.append(g_clean)
        else:
            invalid.append(g)
    return valid, invalid


def validate_investigation_group(group_value):
    """Returns True only if group_value is exactly one of A-I."""
    return group_value in INVESTIGATION_GROUPS
