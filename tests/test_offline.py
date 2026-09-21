"""
tests/test_offline.py

Verifies that the entire pipeline produces no outbound network calls.
Spec: 02_TRD.md §5.1, §7 S11.
"""
from __future__ import annotations

import socket
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _block_socket(*args, **kwargs):
    raise OSError("Network access is blocked in offline mode")


@pytest.fixture
def offline(monkeypatch):
    """Patch socket.socket so any connection attempt raises immediately."""
    monkeypatch.setattr(socket, "socket", _block_socket)
    monkeypatch.setattr(socket, "getaddrinfo", _block_socket)
    monkeypatch.setattr(socket, "create_connection", _block_socket)
    yield


def test_sniff_is_offline(offline, tmp_path):
    """sniff() on a local file must not touch the network."""
    from services.ingest_service import sniff
    from domain.models import DetectedFormat

    csv_path = tmp_path / "test.csv"
    csv_path.write_text("A-PARTY NO,B-PARTY NO,CALL DATE,DURATION,IMEI,IMSI,CALL TYPE\n"
                        "+919999999999,+918888888888,10/09/2026 10:00:00,120,490154203237518,404101234567890,OUT\n")
    result = sniff(csv_path)
    assert result == DetectedFormat.CDR


def test_hash_file_is_offline(offline, tmp_path):
    """hash_file() reads a local file — no network."""
    from services.ingest_service import hash_file
    f = tmp_path / "data.bin"
    f.write_bytes(b"hello world")
    h = hash_file(f)
    assert len(h) == 64


def test_propose_mapping_is_offline(offline):
    """propose_mapping() does only local RapidFuzz computation."""
    from services.ingest_service import propose_mapping
    from domain.models import DetectedFormat
    result = propose_mapping(["A-PARTY NO", "B-PARTY NO", "CALL DATE", "DURATION", "IMEI"], DetectedFormat.CDR)
    assert result is not None


def test_correlate_is_offline(offline):
    """resolve_links and build_graph must not use the network."""
    from services.correlate_service import resolve_links, build_graph
    links = resolve_links([], [], "case_offline")
    assert links == []
    G = build_graph([], [])
    assert G.number_of_nodes() == 0


def test_auth_is_offline(offline):
    """auth_service must not make network calls."""
    from services.auth_service import hash_password, verify_password
    h = hash_password("test_password_123")
    assert verify_password("test_password_123", h)
    assert not verify_password("wrong", h)
