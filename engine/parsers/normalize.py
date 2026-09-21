"""
engine/parsers/normalize.py

Entity normalisation rules from 05_Backend_Schema.md §3.4.
Pre-compiled regexes; vectorisable via Polars `map_elements`.
"""
from __future__ import annotations

import re


_RE_NON_DIGIT = re.compile(r'\D')
_RE_NON_ALNUM = re.compile(r'[^a-z0-9]')


def normalize_phone(raw: str) -> str:
    """E.164 normalisation for Indian numbers. Strips spaces/dashes, adds +91."""
    digits = _RE_NON_DIGIT.sub("", raw)
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+91" + digits[1:]
    return "+" + digits  # best-effort


def _luhn_valid(digits: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def normalize_imei(raw: str) -> str:
    """Digits-only; validates Luhn; returns 15-digit string or raises ValueError."""
    digits = _RE_NON_DIGIT.sub("", raw)
    if len(digits) != 15 or not _luhn_valid(digits):
        raise ValueError(f"Invalid IMEI: {raw!r}")
    return digits


def normalize_imsi(raw: str) -> str:
    """Digits-only, must be 15 digits."""
    digits = _RE_NON_DIGIT.sub("", raw)
    if len(digits) != 15:
        raise ValueError(f"Invalid IMSI: {raw!r}")
    return digits


def normalize_upi(raw: str) -> str:
    """Lowercase, trimmed, @psp suffix preserved."""
    return raw.strip().lower()


def normalize_bank_account(raw: str) -> str:
    """Digits only; preserve leading zeros (only strip when IFSC known — done at caller)."""
    return _RE_NON_DIGIT.sub("", raw)


def normalize_ip(raw: str) -> str:
    """Return the address as-is (normalised by ipaddress if needed)."""
    import ipaddress
    try:
        return str(ipaddress.ip_address(raw.strip()))
    except ValueError:
        return raw.strip()


def normalize_mac(raw: str) -> str:
    """Lowercase colon-separated."""
    digits = _RE_NON_ALNUM.sub("", raw.lower())
    if len(digits) == 12:
        return ":".join(digits[i:i+2] for i in range(0, 12, 2))
    return raw.lower()


def normalize_email(raw: str) -> str:
    """Lowercase domain; preserve local part case."""
    parts = raw.strip().split("@", 1)
    if len(parts) == 2:
        return f"{parts[0]}@{parts[1].lower()}"
    return raw.strip()


NORMALIZERS = {
    "PHONE": normalize_phone,
    "IMEI": normalize_imei,
    "IMSI": normalize_imsi,
    "UPI_HANDLE": normalize_upi,
    "BANK_ACCOUNT": normalize_bank_account,
    "IP": normalize_ip,
    "MAC": normalize_mac,
    "EMAIL": normalize_email,
}


def normalize(entity_type: str, raw: str) -> str:
    fn = NORMALIZERS.get(entity_type)
    if fn is None:
        return raw.strip()
    return fn(raw)
