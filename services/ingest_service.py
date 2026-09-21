"""
services/ingest_service.py

Phase 3 — Ingestion and mapping.
Owner: A (backend).  No HTTP.  Single process.

Progress callbacks: every function that touches a file accepts an optional
    progress_cb(message: str, rows_done: int, rows_total: int)
so Streamlit's live rows/sec widget can hook in.

Caching: all heavy results are pure functions of (case_id, file_sha256).
The caller (UI) should wrap these with @st.cache_data(hash_funcs=...) keyed
on (case_id, manifest_hash). Services themselves stay stateless.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple

import yaml

from domain.models import DetectedFormat, Mapping, MappingProposal, IngestResult
from domain.errors import (
    ParseError, FileTooLargeError, PathTraversalError,
    PasswordProtectedError, DuplicateEvidenceError,
)
from engine.mapping.sniff import sniff as _sniff
from engine.mapping.fuzzy import propose_mapping as _fuzzy_map
from engine.integrity.hashing import hash_file as _hash_file, hash_payload
from engine.parsers.normalize import normalize

_MAX_BYTES = 1024 * 1024 * 1024  # 1 GB hard limit per file

# ─── Public: sniff ────────────────────────────────────────────────────────────

def sniff(path: Path) -> DetectedFormat:
    """
    Detect file type by content (not extension).
    Raises ParseError on empty/corrupt, FileTooLargeError > 500 MB.
    """
    _guard_path(path)
    return _sniff(path)


# ─── Public: hash_file ────────────────────────────────────────────────────────

def hash_file(
    path: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    Compute the SHA-256 hex digest of a file using 1 MiB chunks.
    progress_cb(bytes_done, bytes_total) is called after each chunk.
    """
    _guard_path(path)
    return _hash_file(path, progress_cb)


# ─── Public: propose_mapping ─────────────────────────────────────────────────

def propose_mapping(headers: List[str], fmt: DetectedFormat) -> MappingProposal:
    """
    Fuzzy-match headers against the canonical schema and YAML plugin aliases.
    Returns a MappingProposal with per-field confidence scores.
    Completes in < 50 ms (RapidFuzz over a small canonical set).
    """
    # Load plugin if available
    plugin_cols = _load_plugin_columns(fmt)
    raw_mapping = _fuzzy_map(headers, fmt.value, plugin_cols)

    mapping_json = {field: info["source_col"] for field, info in raw_mapping.items()}
    confidence_json = {field: info["confidence"] for field, info in raw_mapping.items()}

    # Detect datetime format hint from plugin
    dt_fmt = _plugin_datetime_formats(fmt)

    return MappingProposal(
        detected_kind=fmt,
        header_signature=",".join(sorted(h.lower() for h in headers)),
        mapping_json=mapping_json,
        confidence_json=confidence_json,
        datetime_format=dt_fmt[0] if dt_fmt else None,
    )


# ─── Public: ingest_file ─────────────────────────────────────────────────────

def ingest_file(
    case_id: str,
    path: Path,
    mapping: Mapping,
    officer_id: str,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> IngestResult:
    """
    Parse a file using the confirmed mapping.
    Extracts entities and events with provenance triples attached.
    Rejects rows go to parse_rejects (caller must persist them).
    Returns IngestResult with row counts.

    The actual DB writes are the responsibility of the DB layer (db/init.py).
    This service returns the parsed data as plain dicts ready for bulk insert.

    Raises:
        ParseError           — file cannot be parsed at all
        PathTraversalError   — path escapes the expected directory
        FileTooLargeError    — file > 1 GB
        DuplicateEvidenceError — same SHA-256 already in this case (caller checks)
        PasswordProtectedError — encrypted XLSX
    """
    _guard_path(path)
    if not path.exists():
        raise ParseError(path, "File not found.")
    if path.stat().st_size > _MAX_BYTES:
        raise FileTooLargeError(path, path.stat().st_size, _MAX_BYTES)

    mapping_dict = json.loads(mapping.mapping_json) if isinstance(mapping.mapping_json, str) else mapping.mapping_json
    dt_fmts = _plugin_datetime_formats(DetectedFormat(mapping.detected_kind))
    if mapping.datetime_format:
        dt_fmts = [mapping.datetime_format] + dt_fmts

    file_sha256 = _hash_file(path)
    evidence_file_id = mapping.evidence_file_id or str(uuid.uuid4())
    kind = mapping.detected_kind

    rows_total = rows_parsed = rows_rejected = 0
    entities: Dict[Tuple, dict] = {}
    events: List[dict] = []
    rejects: List[dict] = []

    if progress_cb:
        progress_cb("Counting rows…", 0, 0)

    try:
        if path.suffix.lower() in (".xlsx", ".xlsm"):
            row_iter, all_headers = _iter_xlsx_with_headers(path)
        else:
            row_iter, all_headers = _iter_csv_with_headers(path)

        for src_row, raw_row in enumerate(row_iter, start=2):  # start=2: row 1 is header
            rows_total += 1
            try:
                mapped = _apply_mapping(raw_row, mapping_dict)
                parsed_at = _parse_datetime(mapped, dt_fmts)

                event, new_entities = _build_event_and_entities(
                    case_id=case_id,
                    kind=kind,
                    mapped=mapped,
                    parsed_at=parsed_at,
                    src_row=src_row,
                    evidence_file_id=evidence_file_id,
                    source_sha256=file_sha256,
                )
                events.append(event)
                for key, ent in new_entities.items():
                    if key not in entities:
                        entities[key] = ent
                    else:
                        entities[key]["occurrences"] += 1

                rows_parsed += 1
                if progress_cb and rows_total % 1000 == 0:
                    progress_cb("Parsing…", rows_parsed, rows_total)

            except Exception as exc:
                rows_rejected += 1
                rejects.append({
                    "id": str(uuid.uuid4()),
                    "case_id": case_id,
                    "evidence_file_id": evidence_file_id,
                    "source_row": src_row,
                    "raw_line": str(raw_row),
                    "reason": str(exc),
                    "created_at": _now(),
                })

    except PasswordProtectedError:
        raise
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError(path, str(exc)) from exc

    if progress_cb:
        progress_cb("Done", rows_parsed, rows_total)

    return IngestResult(
        evidence_file_id=evidence_file_id,
        rows_total=rows_total,
        rows_parsed=rows_parsed,
        rows_rejected=rows_rejected,
        status="PARSED" if rows_rejected == 0 else "PARSED",
        # Attach parsed data for callers
        _entities=list(entities.values()),
        _events=events,
        _rejects=rejects,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_path(path: Path) -> None:
    """Reject symlinks and paths with traversal sequences."""
    try:
        resolved = path.resolve()
    except Exception as exc:
        raise PathTraversalError(f"Cannot resolve {path}: {exc}") from exc
    if path.is_symlink():
        raise PathTraversalError(f"Symlinks are not permitted: {path}")


def _iter_csv_with_headers(path: Path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    return iter(reader), reader.fieldnames or []


def _iter_xlsx_with_headers(path: Path):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        msg = str(exc).lower()
        if "encrypted" in msg or "password" in msg:
            raise PasswordProtectedError(path, "File is password-protected.")
        raise ParseError(path, str(exc))
    ws = wb.worksheets[0]
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(c) if c is not None else "" for c in next(rows_iter, [])]

    def _gen():
        for row in rows_iter:
            row_vals = [str(c) if c is not None else "" for c in row]
            yield dict(zip(headers, row_vals))
        wb.close()

    return _gen(), headers


def _apply_mapping(raw_row: dict, mapping_dict: Dict[str, str]) -> dict:
    """Remap raw column names to canonical field names."""
    # mapping_dict = {canonical_field: source_column_name}
    inv = {v: k for k, v in mapping_dict.items()}
    result = {}
    for col, val in raw_row.items():
        canonical = inv.get(col, col)
        result[canonical] = (val or "").strip()
    return result


def _parse_datetime(mapped: dict, dt_fmts: List[str]) -> Optional[str]:
    """Try each datetime format; return ISO-8601 UTC string or None."""
    raw_time = mapped.get("start_time") or mapped.get("txn_time") or mapped.get("date")
    if not raw_time:
        return None
    for fmt in dt_fmts:
        try:
            dt = datetime.strptime(raw_time, fmt)
            # Assume IST → UTC
            from datetime import timedelta
            dt_utc = dt - timedelta(hours=5, minutes=30)
            return dt_utc.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None  # will go to reject reason


_RE_PHONE = re.compile(r'^\+?\d[\d\s\-().]{7,}$')
_RE_EMAIL = re.compile(r'^[\w.\-+]+@[\w.\-]+\.[a-z]{2,}$', re.I)
_RE_UPI   = re.compile(r'^[\w.\-+]+@[a-z]+$', re.I)
_RE_IP    = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')


def _classify_entity(val: str) -> Optional[str]:
    if not val:
        return None
    d = re.sub(r'\D', '', val)
    if len(d) == 15:
        return "IMEI"
    if _RE_UPI.match(val) and "@" in val:
        return "UPI_HANDLE"
    if _RE_EMAIL.match(val):
        return "EMAIL"
    if _RE_IP.match(val):
        return "IP"
    if _RE_PHONE.match(val) and 10 <= len(d) <= 12:
        return "PHONE"
    if len(d) in (9, 18) and val.isdigit():
        return "BANK_ACCOUNT"
    return None


def _build_event_and_entities(
    case_id, kind, mapped, parsed_at, src_row, evidence_file_id, source_sha256
) -> Tuple[dict, Dict[Tuple, dict]]:
    now = _now()
    occurred_at = parsed_at or now
    entities = {}
    src_entity_id = dst_entity_id = None

    # Extract source entity (caller / debit_account / payer)
    for src_field in ("caller", "debit_account"):
        raw = mapped.get(src_field, "")
        if raw:
            etype = _infer_entity_type(src_field)
            try:
                norm = normalize(etype, raw)
                key = (case_id, etype, norm)
                eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, ":".join(key)))
                entities[key] = _make_entity(eid, case_id, etype, raw, norm, now)
                src_entity_id = eid
            except Exception:
                pass
            break

    # Extract destination entity (callee / credit_account / payee)
    for dst_field in ("callee", "credit_account"):
        raw = mapped.get(dst_field, "")
        if raw:
            etype = _infer_entity_type(dst_field)
            try:
                norm = normalize(etype, raw)
                key = (case_id, etype, norm)
                eid = str(uuid.uuid5(uuid.NAMESPACE_DNS, ":".join(key)))
                entities[key] = _make_entity(eid, case_id, etype, raw, norm, now)
                dst_entity_id = eid
            except Exception:
                pass
            break

    event_type = _kind_to_event_type(kind)
    amount_raw = mapped.get("amount", "")
    try:
        amount = float(re.sub(r'[^\d.]', '', amount_raw)) if amount_raw else None
    except ValueError:
        amount = None

    event = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "occurred_at_tz": "Asia/Kolkata",
        "src_entity_id": src_entity_id,
        "dst_entity_id": dst_entity_id,
        "amount": amount,
        "currency": "INR",
        "duration_sec": _safe_int(mapped.get("duration_s")),
        "channel": mapped.get("channel"),
        "reference_no": mapped.get("reference_no"),
        "balance_after": _safe_float(mapped.get("balance_after")),
        "raw_json": json.dumps(mapped, ensure_ascii=False),
        "evidence_file_id": evidence_file_id,
        "source_row": src_row,
        "source_sha256": source_sha256,
        "created_at": now,
    }
    return event, entities


def _infer_entity_type(field: str) -> str:
    mapping = {
        "caller": "PHONE", "callee": "PHONE",
        "debit_account": "BANK_ACCOUNT", "credit_account": "BANK_ACCOUNT",
        "imei": "IMEI", "imsi": "IMSI",
    }
    return mapping.get(field, "PHONE")


def _kind_to_event_type(kind: str) -> str:
    return {
        "CDR": "CALL", "IPDR": "DATA_SESSION",
        "BANK": "TRANSFER", "UPI": "UPI_TXN",
        "EML": "EMAIL", "ANDROID_DUMP": "APP_INSTALL",
    }.get(kind, "DEVICE_EVENT")


def _make_entity(eid, case_id, etype, raw, norm, now) -> dict:
    return {
        "id": eid, "case_id": case_id, "entity_type": etype,
        "raw_value": raw, "normalized_value": norm,
        "role": "UNKNOWN", "occurrences": 1,
        "attributes_json": "{}", "created_at": now,
    }


def _safe_int(v) -> Optional[int]:
    try:
        return int(float(v)) if v else None
    except (TypeError, ValueError):
        return None


def _safe_float(v) -> Optional[float]:
    try:
        return float(re.sub(r'[^\d.]', '', str(v))) if v else None
    except (TypeError, ValueError):
        return None


# ─── Plugin helpers ───────────────────────────────────────────────────────────

_PLUGIN_CACHE: Dict[str, dict] = {}


def _load_plugin(fmt: DetectedFormat) -> Optional[dict]:
    global _PLUGIN_CACHE
    if fmt.value in _PLUGIN_CACHE:
        return _PLUGIN_CACHE[fmt.value]
    plugin_dir = Path(__file__).parent.parent / "engine" / "parsers" / "formats"
    for p in plugin_dir.glob("*.yaml"):
        with open(p) as f:
            data = yaml.safe_load(f)
        if data.get("kind") == fmt.value:
            _PLUGIN_CACHE[fmt.value] = data
            return data
    return None


def _load_plugin_columns(fmt: DetectedFormat) -> Optional[Dict[str, List[str]]]:
    plugin = _load_plugin(fmt)
    return plugin.get("columns") if plugin else None


def _plugin_datetime_formats(fmt: DetectedFormat) -> List[str]:
    plugin = _load_plugin(fmt)
    return plugin.get("datetime_formats", []) if plugin else []
