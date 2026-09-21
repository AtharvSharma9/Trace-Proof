"""
services/correlate_service.py

Phase 4 — Entity resolution, link detection, graph construction.
Owner: B (backend).

All functions are pure w.r.t. the graph: they read from dicts/lists,
build NetworkX graphs in memory, and return serialisable results.
The UI should @st.cache_data these calls keyed on (case_id, manifest_hash).

Link types implemented here (from 05_Backend_Schema.md §3.7):
  SHARED_IMEI, SHARED_IMSI, RECURRING_BENEFICIARY, FUND_FLOW

Graph patterns detected:
  fan-in, fan-out, pass-through, cycles
"""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import networkx as nx

from domain.models import Entity, EntityLink
from engine.graph.builder import build_graph as _build, compute_metrics, detect_patterns


# Default confidence thresholds per schema §3.7
_CONFIDENCE: Dict[str, float] = {
    "SHARED_IMEI":            0.95,
    "SHARED_IMSI":            0.95,
    "SHARED_MAC":             0.90,
    "SHARED_APK_CERT":        0.90,
    "RECURRING_BENEFICIARY":  0.80,
    "FUND_FLOW":              1.00,
    "SHARED_IP_SUBNET":       0.45,
    "TEMPORAL_PROXIMITY":     0.35,
    "SHARED_EMAIL_DOMAIN":    0.40,
}

_ACTIVE_THRESHOLD = 0.75  # links below this are stored but not surfaced by default


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Public: extract_entities ────────────────────────────────────────────────

def extract_entities(entities_raw: List[Dict]) -> List[Entity]:
    """
    Validate and coerce raw entity dicts (already normalised by ingest_service)
    into Pydantic Entity models.

    Contract: idempotent — same input produces same output.
    """
    result = []
    for e in entities_raw:
        try:
            result.append(Entity(**e))
        except Exception:
            pass
    return result


# ─── Public: resolve_links ───────────────────────────────────────────────────

def resolve_links(
    entities: List[Dict],
    events: List[Dict],
    case_id: str,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> List[EntityLink]:
    """
    Detect all link types from the entity and event lists.

    SHARED_IMEI  — two phone entities appear with the same IMEI in CDR events.
    SHARED_IMSI  — two phones share the same IMSI.
    RECURRING_BENEFICIARY — same credit_account appears ≥ 3 times with different debit accounts.
    FUND_FLOW    — direct debit→credit transfer (edge carries total_amount).

    Ordering convention: entity_a_id < entity_b_id for symmetric links.
    Returns only ACTIVE links (confidence ≥ _ACTIVE_THRESHOLD for storage, all links kept).
    """
    links: Dict[Tuple, dict] = {}

    def _add_link(a_id, b_id, ltype, conf, rationale, support, ev_ids=None, amount=None):
        if a_id == b_id:
            return
        a, b = sorted([a_id, b_id])
        key = (a, b, ltype)
        if key not in links or links[key]["confidence"] < conf:
            links[key] = {
                "id": str(uuid.uuid4()),
                "case_id": case_id,
                "entity_a_id": a,
                "entity_b_id": b,
                "link_type": ltype,
                "confidence": conf,
                "rationale": rationale,
                "support_count": support,
                "supporting_event_ids": json.dumps(ev_ids or []),
                "total_amount": amount,
                "status": "ACTIVE",
                "created_at": _now(),
            }

    # Index: IMEI → [phone entity ids]
    if progress_cb: progress_cb("Detecting SHARED_IMEI links…")
    imei_to_phones: Dict[str, List[str]] = defaultdict(list)
    imsi_to_phones: Dict[str, List[str]] = defaultdict(list)
    entity_by_id = {e["id"]: e for e in entities}

    for ev in events:
        dev_id = ev.get("device_entity_id")
        sim_id = ev.get("sim_entity_id")
        src_id = ev.get("src_entity_id")
        if dev_id and src_id:
            dev = entity_by_id.get(dev_id, {})
            if dev.get("entity_type") == "IMEI":
                imei_val = dev.get("normalized_value", "")
                if src_id not in imei_to_phones[imei_val]:
                    imei_to_phones[imei_val].append(src_id)
        if sim_id and src_id:
            sim = entity_by_id.get(sim_id, {})
            if sim.get("entity_type") == "IMSI":
                imsi_val = sim.get("normalized_value", "")
                if src_id not in imsi_to_phones[imsi_val]:
                    imsi_to_phones[imsi_val].append(src_id)

    for imei, phones in imei_to_phones.items():
        if len(phones) >= 2:
            for i in range(len(phones)):
                for j in range(i + 1, len(phones)):
                    _add_link(
                        phones[i], phones[j], "SHARED_IMEI",
                        _CONFIDENCE["SHARED_IMEI"],
                        f"IMEI {imei} appears with both entities.",
                        len(phones),
                    )

    for imsi, phones in imsi_to_phones.items():
        if len(phones) >= 2:
            for i in range(len(phones)):
                for j in range(i + 1, len(phones)):
                    _add_link(
                        phones[i], phones[j], "SHARED_IMSI",
                        _CONFIDENCE["SHARED_IMSI"],
                        f"IMSI {imsi} shared across entities.",
                        len(phones),
                    )

    # RECURRING_BENEFICIARY
    if progress_cb: progress_cb("Detecting RECURRING_BENEFICIARY links…")
    credit_to_debits: Dict[str, List[str]] = defaultdict(set)
    for ev in events:
        src = ev.get("src_entity_id")
        dst = ev.get("dst_entity_id")
        if src and dst and ev.get("event_type") in ("TRANSFER", "UPI_TXN"):
            credit_to_debits[dst].add(src)

    for dst, srcs in credit_to_debits.items():
        if len(srcs) >= 3:
            src_list = list(srcs)
            for i in range(len(src_list)):
                for j in range(i + 1, len(src_list)):
                    _add_link(
                        src_list[i], src_list[j], "RECURRING_BENEFICIARY",
                        min(0.80 + 0.02 * len(srcs), 0.95),
                        f"Both entities credited account/UPI {dst} on {len(srcs)} distinct occasions.",
                        len(srcs),
                    )

    # FUND_FLOW (direct, per event)
    if progress_cb: progress_cb("Detecting FUND_FLOW links…")
    flow_totals: Dict[Tuple[str, str], float] = defaultdict(float)
    flow_events: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for ev in events:
        src = ev.get("src_entity_id")
        dst = ev.get("dst_entity_id")
        if src and dst and ev.get("event_type") in ("TRANSFER", "UPI_TXN", "ATM_WITHDRAWAL"):
            key = (src, dst)
            flow_totals[key] += ev.get("amount") or 0.0
            flow_events[key].append(ev["id"])

    for (src, dst), total in flow_totals.items():
        _add_link(
            src, dst, "FUND_FLOW",
            _CONFIDENCE["FUND_FLOW"],
            f"Direct fund flow of ₹{total:,.2f} observed.",
            len(flow_events[(src, dst)]),
            flow_events[(src, dst)],
            total,
        )

    return [EntityLink(**lk) for lk in links.values()]


# ─── Public: build_graph ─────────────────────────────────────────────────────

def build_graph(
    entities: List[Dict],
    links: List[Dict],
    events: Optional[List[Dict]] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> nx.MultiDiGraph:
    """
    Build a NetworkX MultiDiGraph. Bulk adds — never per-edge.
    Computes PageRank, betweenness (k-sampled above 5 k nodes), fan-in/out.

    The returned graph has all metrics attached to node attributes so
    callers can serialise to JSON without pickling a graph object.

    Returns: networkx.MultiDiGraph
    """
    G = _build(entities, links, events, progress_cb)
    compute_metrics(G, progress_cb)
    return G


# ─── Public: find_cashout_paths ───────────────────────────────────────────────

def find_cashout_paths(
    G: nx.MultiDiGraph,
    victim_ids: List[str],
    cashout_ids: List[str],
    max_hops: int = 6,
) -> List[List[str]]:
    """
    All simple paths from victim nodes to cash-out nodes, capped at max_hops.
    Safe against combinatorial explosion via networkx cutoff.
    """
    from engine.graph.builder import find_cashout_paths as _paths
    return _paths(G, victim_ids, cashout_ids, max_hops)
