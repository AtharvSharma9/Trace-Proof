"""
engine/mapping/sniff.py

Content-based file type detection.  Never trusts the file extension.
Returns a DetectedFormat enum member.
"""
from __future__ import annotations

import re
import csv
import io
from pathlib import Path
from typing import List

import yaml

from domain.models import DetectedFormat
from domain.errors import ParseError, FileTooLargeError

# Max file size we will sniff (not a hard parse limit – parsers enforce their own).
_MAX_SNIFF_BYTES = 500 * 1024 * 1024  # 500 MB

# Luhn check for IMEI
def _luhn_valid(s: str) -> bool:
    digits = [int(c) for c in s]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

_RE_IMEI = re.compile(r'\b\d{15}\b')
_RE_UPI  = re.compile(r'\b[\w.\-+]+@[a-z]+\b', re.I)
_RE_RECEIVED = re.compile(r'^Received:', re.I | re.M)

# Load YAML plugins once at import time
def _load_plugins() -> list[dict]:
    plugin_dir = Path(__file__).parent.parent / "parsers" / "formats"
    plugins = []
    for p in plugin_dir.glob("*.yaml"):
        with open(p, encoding="utf-8") as f:
            plugins.append(yaml.safe_load(f))
    return plugins

_PLUGINS: list[dict] = []

def _get_plugins() -> list[dict]:
    global _PLUGINS
    if not _PLUGINS:
        _PLUGINS = _load_plugins()
    return _PLUGINS


def _normalise_header(h: str) -> str:
    return re.sub(r'[^a-z0-9]', ' ', h.lower()).strip()


def _detect_by_plugin(headers: List[str]) -> DetectedFormat | None:
    """Match normalised headers against plugin signatures."""
    norm = {_normalise_header(h) for h in headers}
    for plugin in _get_plugins():
        required = [_normalise_header(m) for m in plugin["detect"]["any_header_matches"]]
        min_matches = plugin["detect"].get("min_matches", 2)
        hits = sum(1 for r in required if any(r in n for n in norm))
        if hits >= min_matches:
            return DetectedFormat(plugin["kind"])
    return None


def _read_head(path: Path, n_rows: int = 5) -> tuple[List[str], str]:
    """Return (headers, first_n_rows_as_text) from a CSV-like file."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.reader(io.StringIO(text))
    rows = []
    for i, row in enumerate(reader):
        if i >= n_rows + 1:
            break
        rows.append(row)
    headers = rows[0] if rows else []
    body = "\n".join(",".join(r) for r in rows[1:])
    return headers, body


def sniff(path: Path) -> DetectedFormat:
    """
    Detect the file type by content, not extension.

    Reads up to 5 rows of headers from CSV/XLSX and matches against YAML
    format plugins. Falls back to regex content sniffing for EML and
    JSON dumps. Raises ParseError on zero-byte files, FileTooLargeError
    when the file exceeds 500 MB.
    """
    if not path.exists():
        raise ParseError(path, "File not found.")
    size = path.stat().st_size
    if size == 0:
        raise ParseError(path, "File is empty.")
    if size > _MAX_SNIFF_BYTES:
        raise FileTooLargeError(path, size, _MAX_SNIFF_BYTES)

    suffix = path.suffix.lower()

    # EML: check Received: header lines
    if suffix == ".eml":
        try:
            snippet = path.read_bytes()[:4096].decode("utf-8", errors="replace")
            if _RE_RECEIVED.search(snippet):
                return DetectedFormat.EML
        except Exception:
            pass

    # JSON: look for android_dump markers
    if suffix == ".json":
        try:
            snippet = path.read_bytes()[:2048].decode("utf-8", errors="replace")
            if any(k in snippet for k in ("call_log", "sms_log", "contacts", "android")):
                return DetectedFormat.ANDROID_DUMP
        except Exception:
            pass

    # XLSX
    if suffix in (".xlsx", ".xlsm", ".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.worksheets[0]
            headers = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 0:
                    headers = [str(c or "") for c in row]
                    break
            wb.close()
            result = _detect_by_plugin(headers)
            if result:
                return result
        except Exception as exc:
            msg = str(exc).lower()
            if "encrypted" in msg or "password" in msg:
                from domain.errors import PasswordProtectedError
                raise PasswordProtectedError(path, "File is password-protected.")
            raise ParseError(path, f"Cannot read XLSX: {exc}")

    # CSV / TSV
    try:
        headers, body = _read_head(path)
        result = _detect_by_plugin(headers)
        if result:
            return result

        # Content-level regex fallback
        imei_hits = _RE_IMEI.findall(body)
        valid_imei = [s for s in imei_hits if _luhn_valid(s)]
        if valid_imei:
            return DetectedFormat.CDR
        upi_hits = _RE_UPI.findall(body)
        if upi_hits:
            return DetectedFormat.UPI
    except Exception:
        pass

    return DetectedFormat.UNKNOWN
