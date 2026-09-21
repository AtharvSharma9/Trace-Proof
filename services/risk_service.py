"""
services/risk_service.py
========================
Phase 5 — Fraud Risk Scoring & Explanation Service.
Orchestrates:
  1. Feature extraction from the correlation graph (NetworkX MultiDiGraph) & events.
  2. Rule scoring (R01–R12) and court-admissible explanation generation (RiskReasons).
  3. Isolation Forest anomaly re-ranking within risk bands.
  4. Packaging into domain RiskScore models with complete auditability.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

import networkx as nx
import numpy as np
import pandas as pd

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False

# Anomaly detection layer
from engine.anomaly import apply_anomaly_reranking, run_anomaly_detection
from engine.anomaly.isolation_forest import FEATURE_COLUMNS, MODEL_VERSION, RANDOM_STATE

# Rule engine
from engine.rules import (
    compute_weights_hash,
    evaluate_entity_features,
    load_rules_config,
)

# Domain models with fallback
try:
    from domain.models import RiskReason, RiskScore
except ImportError:
    from pydantic import BaseModel, ConfigDict, Field

    class RiskReason(BaseModel):  # type: ignore[no-redef]
        id: str
        risk_score_id: str
        rule_code: str
        rule_name: str
        triggered: int
        raw_value: Optional[float] = None
        threshold: Optional[float] = None
        weight: float
        points_contributed: float
        plain_text: str
        display_order: int

    class RiskScore(BaseModel):  # type: ignore[no-redef]
        model_config = ConfigDict(protected_namespaces=())
        id: str
        case_id: str
        entity_id: str
        score: float
        band: str
        rules_score: float
        anomaly_score: Optional[float] = None
        anomaly_used: int = 0
        rank_in_case: Optional[int] = None
        features_json: str
        model_version: str
        weights_hash: str
        random_seed: Optional[int] = None
        computed_by_badge: str
        computed_at: str
        is_current: int = 1
        reasons: List[RiskReason] = Field(default_factory=list)

logger = logging.getLogger(__name__)


# ── Helper: bounded layering depth calculation ──────────────────────────────
def _compute_node_layering_depth(g: nx.MultiDiGraph, node: str, max_depth: int = 6) -> int:
    """
    Computes the maximum forward hop length in fund flow from the given node.
    Bounded by max_depth to prevent infinite loops on graph cycles.
    """
    if g.out_degree(node) == 0:
        return 0

    visited = {node}
    current_level = {node}
    depth = 0

    while current_level and depth < max_depth:
        next_level = set()
        for u in current_level:
            for v in g.successors(u):
                if v not in visited:
                    visited.add(v)
                    next_level.add(v)
        if next_level:
            depth += 1
            current_level = next_level
        else:
            break

    return depth


# ── Step 1: Feature Extraction ───────────────────────────────────────────────
def compute_features(
    g: Any,
    events: Optional[List[Dict[str, Any]]] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    case_id: Optional[str] = None,
) -> Any:
    """
    Computes feature metrics for each entity from the graph and event history.
    Extracts features required by R01–R12 rules and the IsolationForest model.

    Returns:
        polars.DataFrame (if polars installed) or pandas.DataFrame containing
        one row per entity with all standard feature columns.
    """
    if g is None or not isinstance(g, (nx.Graph, nx.MultiDiGraph)):
        # Return empty frame
        empty_cols = ["entity_id"] + FEATURE_COLUMNS
        df_empty = pd.DataFrame(columns=empty_cols)
        return pl.from_pandas(df_empty) if HAS_POLARS else df_empty

    # Ensure centrality metrics exist
    nodes = list(g.nodes())
    if not nodes:
        df_empty = pd.DataFrame(columns=["entity_id"] + FEATURE_COLUMNS)
        return pl.from_pandas(df_empty) if HAS_POLARS else df_empty

    # Pre-calculate graph centralities if not already attached
    sample_node = nodes[0]
    has_centrality = "betweenness" in g.nodes[sample_node] and "pagerank" in g.nodes[sample_node]

    if not has_centrality:
        try:
            pr_dict = nx.pagerank(g, alpha=0.85, max_iter=100)
        except Exception:
            pr_dict = {n: 1.0 / len(nodes) for n in nodes}

        if len(nodes) > 5000:
            bc_dict = nx.betweenness_centrality(g, k=500, normalized=True)
        else:
            bc_dict = nx.betweenness_centrality(g, normalized=True)
    else:
        pr_dict = {n: g.nodes[n].get("pagerank", 0.0) for n in nodes}
        bc_dict = {n: g.nodes[n].get("betweenness", 0.0) for n in nodes}

    # Aggregate transaction amounts per node
    in_amounts: Dict[str, float] = {n: 0.0 for n in nodes}
    out_amounts: Dict[str, float] = {n: 0.0 for n in nodes}
    in_counts: Dict[str, int] = {n: 0 for n in nodes}
    out_counts: Dict[str, int] = {n: 0 for n in nodes}

    # Traverse edges for fund flow sums
    for u, v, data in g.edges(data=True):
        amt = float(data.get("amount") or 0.0)
        out_amounts[u] = out_amounts.get(u, 0.0) + amt
        out_counts[u] = out_counts.get(u, 0) + 1
        in_amounts[v] = in_amounts.get(v, 0.0) + amt
        in_counts[v] = in_counts.get(v, 0) + 1

    # Event-level features
    odd_hour_counts: Dict[str, int] = {n: 0 for n in nodes}
    sim_counts: Dict[str, int] = {n: 1 for n in nodes}
    device_share_counts: Dict[str, int] = {n: 1 for n in nodes}
    cashout_flags: Dict[str, int] = {n: 0 for n in nodes}
    spoofed_flags: Dict[str, int] = {n: 0 for n in nodes}
    call_transfer_flags: Dict[str, int] = {n: 0 for n in nodes}

    if events:
        for ev in events:
            src = ev.get("src_entity_id")
            dst = ev.get("dst_entity_id")
            ev_type = ev.get("event_type", "")
            occurred_at_str = ev.get("occurred_at", "")

            # Check odd hours 00:00 to 05:00
            if occurred_at_str:
                try:
                    dt = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
                    if dt.hour < 5:
                        if src and src in odd_hour_counts:
                            odd_hour_counts[src] += 1
                        if dst and dst in odd_hour_counts:
                            odd_hour_counts[dst] += 1
                except Exception:
                    pass

            # Cash-out check
            if ev_type in ("ATM_WITHDRAWAL", "CASHOUT"):
                if src and src in cashout_flags:
                    cashout_flags[src] = 1
                if dst and dst in cashout_flags:
                    cashout_flags[dst] = 1

    # Entity attribute overrides
    entity_age_map: Dict[str, float] = {}
    if entities:
        for e in entities:
            eid = e.get("id")
            if not eid:
                continue
            # Extract account age or first seen
            attrs = e.get("attributes_json", "{}")
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except Exception:
                    attrs = {}
            age = float(attrs.get("account_age_days", 365.0))
            entity_age_map[eid] = age

    # Assemble feature rows
    rows: List[Dict[str, Any]] = []
    for node in nodes:
        node_data = g.nodes[node]
        in_amt = in_amounts.get(node, 0.0)
        out_amt = out_amounts.get(node, 0.0)
        tot_turnover = round(in_amt + out_amt, 2)

        # Pass-through ratio
        if in_amt > 0:
            passthrough = min(1.0, max(0.0, round(out_amt / in_amt, 4)))
        else:
            passthrough = node_data.get("passthrough_ratio", 0.0)

        # Layering depth
        if "layering_depth" in node_data:
            layering = int(node_data["layering_depth"])
        elif isinstance(g, nx.MultiDiGraph):
            layering = _compute_node_layering_depth(g, node)
        else:
            layering = 0

        # Neighbors
        if isinstance(g, nx.MultiDiGraph):
            in_deg = g.in_degree(node)
            out_deg = g.out_degree(node)
            unique_cp = len(set(g.predecessors(node)).union(set(g.successors(node))))
        else:
            in_deg = g.degree(node)
            out_deg = g.degree(node)
            unique_cp = len(list(g.neighbors(node)))

        fan_in = in_counts.get(node, in_deg)
        fan_out = out_counts.get(node, out_deg)

        row = {
            "entity_id": node,
            "passthrough_ratio": float(node_data.get("passthrough_ratio", passthrough)),
            "fan_in_count": int(node_data.get("fan_in_count", fan_in)),
            "fan_out_count": int(node_data.get("fan_out_count", fan_out)),
            "layering_depth": int(layering),
            "sim_switch_count": int(node_data.get("sim_switch_count", sim_counts.get(node, 1))),
            "device_share_count": int(node_data.get("device_share_count", device_share_counts.get(node, 1))),
            "account_age_days": float(entity_age_map.get(node, node_data.get("account_age_days", 365.0))),
            "total_turnover": float(node_data.get("total_turnover", tot_turnover)),
            "odd_hour_txn_count": int(node_data.get("odd_hour_txn_count", odd_hour_counts.get(node, 0))),
            "betweenness_centrality": float(bc_dict.get(node, 0.0)),
            "pagerank": float(pr_dict.get(node, 0.0)),
            "in_degree": int(in_deg),
            "out_degree": int(out_deg),
            "unique_counterparties": int(unique_cp),
            # Optional flags for specialized rules
            "is_cashout_terminal": int(node_data.get("is_cashout_terminal", cashout_flags.get(node, 0))),
            "has_spoofed_header": int(node_data.get("has_spoofed_header", spoofed_flags.get(node, 0))),
            "has_call_then_transfer": int(node_data.get("has_call_then_transfer", call_transfer_flags.get(node, 0))),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return pl.from_pandas(df) if HAS_POLARS else df


# ── Step 2: Scoring Orchestration ────────────────────────────────────────────
def score(
    case_id: str,
    g: Any = None,
    events: Optional[List[Dict[str, Any]]] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    features_df: Any = None,
    use_anomaly: bool = True,
    officer_badge: str = "IO-SYSTEM",
) -> List[RiskScore]:
    """
    Scores entities using the weighted rules (R01–R12) and optionally an
    Isolation Forest to re-rank the entities within bands. Generates RiskReason entries.

    Parameters:
        case_id: The unique case identifier.
        g: Correlation NetworkX MultiDiGraph (optional if features_df provided).
        events: Case event records (optional).
        entities: Case entity records (optional).
        features_df: Precomputed feature frame (pandas or polars).
        use_anomaly: Whether to apply Isolation Forest re-ranking (default True).
        officer_badge: Badge identifier of the officer/system computing the score.

    Returns:
        List of domain RiskScore objects containing complete reason breakdowns.
    """
    # 1. Obtain feature dataframe
    if features_df is None:
        if g is not None:
            features_df = compute_features(g, events=events, entities=entities, case_id=case_id)
        else:
            return []

    # Convert to pandas if polars was passed
    if HAS_POLARS and isinstance(features_df, pl.DataFrame):
        pdf = features_df.to_pandas()
    elif isinstance(features_df, pd.DataFrame):
        pdf = features_df.copy()
    else:
        pdf = pd.DataFrame(features_df)

    if pdf.empty or "entity_id" not in pdf.columns:
        return []

    # 2. Load rules config & compute hash
    config = load_rules_config()
    weights_hash = compute_weights_hash(config)
    now_iso = datetime.now(timezone.utc).isoformat()

    # 3. Evaluate rules R01–R12 on each entity
    scored_records: List[Dict[str, Any]] = []
    for _, row in pdf.iterrows():
        entity_dict = row.to_dict()
        eid = str(entity_dict["entity_id"])
        score_id = f"rs_{case_id}_{eid}"

        rules_score, band, reasons, rule_results = evaluate_entity_features(
            features=entity_dict,
            risk_score_id=score_id,
            config=config,
        )

        scored_records.append({
            "score_id": score_id,
            "entity_id": eid,
            "rules_score": rules_score,
            "band": band,
            "reasons": reasons,
            "features_dict": entity_dict,
        })

    scores_df = pd.DataFrame(scored_records)

    # 4. Apply Anomaly Detection & Re-ranking if requested
    anomaly_output = None
    if use_anomaly:
        # Prepare feature columns for isolation forest
        avail_cols = [c for c in FEATURE_COLUMNS if c in pdf.columns]
        iso_df = pdf[["entity_id"] + avail_cols].copy()

        anomaly_output = run_anomaly_detection(
            features_df=iso_df,
            entity_id_col="entity_id",
        )

        scores_df = apply_anomaly_reranking(
            risk_scores_df=scores_df,
            anomaly_output=anomaly_output,
            entity_id_col="entity_id",
            score_col="rules_score",
            band_col="band",
        )
    else:
        # Default ranking: descending rules_score
        scores_df = scores_df.sort_values(by=["rules_score"], ascending=False).reset_index(drop=True)
        scores_df["final_rank"] = range(1, len(scores_df) + 1)
        scores_df["anomaly_score"] = None

    # 5. Build RiskScore domain models
    final_risk_scores: List[RiskScore] = []
    for _, row in scores_df.iterrows():
        eid = str(row["entity_id"])
        rs_score = float(row["rules_score"])
        anom_val = float(row["anomaly_score"]) if pd.notna(row.get("anomaly_score")) else None
        used_anom = 1 if (use_anomaly and anomaly_output and not anomaly_output.skipped) else 0

        risk_score_obj = RiskScore(
            id=str(row["score_id"]),
            case_id=case_id,
            entity_id=eid,
            score=rs_score,
            band=str(row["band"]),
            rules_score=rs_score,
            anomaly_score=anom_val,
            anomaly_used=used_anom,
            rank_in_case=int(row["final_rank"]),
            features_json=json.dumps(row["features_dict"]),
            model_version=MODEL_VERSION,
            weights_hash=weights_hash,
            random_seed=RANDOM_STATE,
            computed_by_badge=officer_badge,
            computed_at=now_iso,
            is_current=1,
            reasons=row["reasons"],
        )
        final_risk_scores.append(risk_score_obj)

    return final_risk_scores
