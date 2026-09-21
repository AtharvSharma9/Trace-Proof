"""
tests/test_phase5_risk.py
=========================
Phase 5 Test Suite:
- Validates pure functions R01–R12 with triggered and non-triggered feature inputs.
- Validates score capping at 100.0 and risk band boundaries.
- Validates weights hashing determinism.
- Validates graph feature extraction (compute_features).
- Validates that Isolation Forest re-ranking preserves risk bands.
- Validates graceful degradation when samples < 30.
- Validates that every triggered reason carries evidence references.
"""

from __future__ import annotations

import json
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd
import pytest

from engine.rules import (
    DEFAULT_CONFIG,
    compute_weights_hash,
    determine_band,
    evaluate_entity_features,
    load_rules_config,
)
from engine.rules.rules import (
    evaluate_r01,
    evaluate_r02,
    evaluate_r03,
    evaluate_r04,
    evaluate_r05,
    evaluate_r06,
    evaluate_r07,
    evaluate_r08,
    evaluate_r09,
    evaluate_r10,
    evaluate_r11,
    evaluate_r12,
)
from services import risk_service


# ── 1. Pure Rules Tests ───────────────────────────────────────────────────────

def test_r01_rapid_passthrough():
    cfg = DEFAULT_CONFIG["rules"]["R01"]
    # Triggered (95% > 85%)
    res_trig = evaluate_r01({"passthrough_ratio": 0.95}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 18.0
    assert "Forwarded 95.0%" in res_trig.plain_text

    # Not triggered (20% < 85%)
    res_notrig = evaluate_r01({"passthrough_ratio": 0.20}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r02_fan_in():
    cfg = DEFAULT_CONFIG["rules"]["R02"]
    res_trig = evaluate_r02({"fan_in_count": 10}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 12.0

    res_notrig = evaluate_r02({"fan_in_count": 3}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r03_fan_out():
    cfg = DEFAULT_CONFIG["rules"]["R03"]
    res_trig = evaluate_r03({"fan_out_count": 12}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 12.0

    res_notrig = evaluate_r03({"fan_out_count": 2}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r04_layering_depth():
    cfg = DEFAULT_CONFIG["rules"]["R04"]
    res_trig = evaluate_r04({"layering_depth": 4}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 12.0

    res_notrig = evaluate_r04({"layering_depth": 1}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r05_sim_switch():
    cfg = DEFAULT_CONFIG["rules"]["R05"]
    res_trig = evaluate_r05({"sim_switch_count": 3}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 10.0

    res_notrig = evaluate_r05({"sim_switch_count": 1}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r06_device_sharing():
    cfg = DEFAULT_CONFIG["rules"]["R06"]
    res_trig = evaluate_r06({"device_share_count": 4}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 8.0

    res_notrig = evaluate_r06({"device_share_count": 1}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r07_new_account_high_volume():
    cfg = DEFAULT_CONFIG["rules"]["R07"]
    res_trig = evaluate_r07({"account_age_days": 10, "total_turnover": 600000.0}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 10.0

    # High turnover but old account
    res_old = evaluate_r07({"account_age_days": 120, "total_turnover": 600000.0}, cfg)
    assert res_old.triggered == 0

    # New account but low turnover
    res_low = evaluate_r07({"account_age_days": 10, "total_turnover": 50000.0}, cfg)
    assert res_low.triggered == 0


def test_r08_cashout_terminal():
    cfg = DEFAULT_CONFIG["rules"]["R08"]
    res_trig = evaluate_r08({"is_cashout_terminal": 1}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 14.0

    res_notrig = evaluate_r08({"is_cashout_terminal": 0}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r09_spoofed_header():
    cfg = DEFAULT_CONFIG["rules"]["R09"]
    res_trig = evaluate_r09({"has_spoofed_header": 1}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 8.0

    res_notrig = evaluate_r09({"has_spoofed_header": 0}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r10_odd_hour_burst():
    cfg = DEFAULT_CONFIG["rules"]["R10"]
    res_trig = evaluate_r10({"odd_hour_txn_count": 7}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 5.0

    res_notrig = evaluate_r10({"odd_hour_txn_count": 2}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r11_call_then_transfer():
    cfg = DEFAULT_CONFIG["rules"]["R11"]
    res_trig = evaluate_r11({"has_call_then_transfer": 1}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 12.0

    res_notrig = evaluate_r11({"has_call_then_transfer": 0}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


def test_r12_centrality():
    cfg = DEFAULT_CONFIG["rules"]["R12"]
    res_trig = evaluate_r12({"betweenness_centrality": 0.12}, cfg)
    assert res_trig.triggered == 1
    assert res_trig.points_contributed == 10.0

    res_notrig = evaluate_r12({"betweenness_centrality": 0.01}, cfg)
    assert res_notrig.triggered == 0
    assert res_notrig.points_contributed == 0.0


# ── 2. Evaluation, Capping & Banding ──────────────────────────────────────────

def test_weights_hash_deterministic():
    h1 = compute_weights_hash()
    h2 = compute_weights_hash()
    assert len(h1) == 64
    assert h1 == h2


def test_score_capping_and_banding():
    # If all rules trigger, sum is 121, but score must cap at 100
    extreme_features = {
        "entity_id": "MULE_MAX",
        "passthrough_ratio": 0.99,
        "fan_in_count": 20,
        "fan_out_count": 20,
        "layering_depth": 5,
        "sim_switch_count": 5,
        "device_share_count": 5,
        "account_age_days": 10,
        "total_turnover": 1000000.0,
        "is_cashout_terminal": 1,
        "has_spoofed_header": 1,
        "odd_hour_txn_count": 10,
        "has_call_then_transfer": 1,
        "betweenness_centrality": 0.25,
    }

    score, band, reasons, results = evaluate_entity_features(extreme_features)
    assert score == 100.0
    assert band == "CRITICAL"
    assert len(reasons) == 12
    assert all(r.triggered == 1 for r in reasons)
    assert all(r.points_contributed > 0 for r in reasons)

    # Clean profile: zero points
    clean_features = {"entity_id": "INNOCENT_01"}
    score_clean, band_clean, reasons_clean, _ = evaluate_entity_features(clean_features)
    assert score_clean == 0.0
    assert band_clean == "LOW"
    assert len(reasons_clean) == 12
    assert all(r.triggered == 0 for r in reasons_clean)
    assert all(r.points_contributed == 0.0 for r in reasons_clean)


def test_evidence_refs_present_on_triggered_rules():
    features = {
        "entity_id": "TEST_ENTITY",
        "passthrough_ratio": 0.95,
        "passthrough_evidence_refs": ["EV-001", "EV-002"],
    }
    _, _, reasons, results = evaluate_entity_features(features)
    r01_res = next(r for r in results if r.rule_code == "R01")
    assert r01_res.triggered == 1
    assert len(r01_res.evidence_refs) > 0


# ── 3. Graph Feature Extraction ──────────────────────────────────────────────

def test_compute_features_from_graph():
    G = nx.MultiDiGraph()
    # Simple chain: A -> B -> C
    G.add_node("A", entity_id="A")
    G.add_node("B", entity_id="B")
    G.add_node("C", entity_id="C")

    G.add_edge("A", "B", key="FUND_FLOW", amount=100000.0)
    G.add_edge("B", "C", key="FUND_FLOW", amount=95000.0)

    events = [
        {"src_entity_id": "A", "dst_entity_id": "B", "event_type": "TRANSFER", "amount": 100000.0},
        {"src_entity_id": "B", "dst_entity_id": "C", "event_type": "TRANSFER", "amount": 95000.0},
    ]

    features_df = risk_service.compute_features(G, events=events)
    pdf = features_df.to_pandas() if hasattr(features_df, "to_pandas") else features_df

    assert len(pdf) == 3
    b_row = pdf[pdf["entity_id"] == "B"].iloc[0]
    # B received 100k, sent 95k -> passthrough = 0.95
    assert pytest.approx(b_row["passthrough_ratio"], 0.01) == 0.95
    assert b_row["total_turnover"] == 195000.0
    assert b_row["layering_depth"] >= 1


# ── 4. End-to-end Risk Service Scoring with Anomaly Re-ranking ───────────────

def test_risk_service_score_with_mock_dataset():
    data_path = Path(__file__).resolve().parents[1] / "tools" / "mockgen" / "data" / "mock_features_small.csv"
    if not data_path.exists():
        pytest.skip("mock_features_small.csv not found")

    df = pd.read_csv(data_path)
    scores = risk_service.score("case_test", features_df=df, use_anomaly=True)

    assert len(scores) == len(df)
    # Check that scores are typed RiskScore domain models
    assert all(hasattr(s, "score") and hasattr(s, "band") for s in scores)
    assert all(s.score >= 0.0 and s.score <= 100.0 for s in scores)
    assert all(len(s.reasons) == 12 for s in scores)
    from engine.anomaly.isolation_forest import MODEL_VERSION
    assert all(s.model_version == MODEL_VERSION for s in scores)

    # Verify rank order exists
    ranks = [s.rank_in_case for s in scores]
    assert sorted(ranks) == list(range(1, len(df) + 1))


def test_anomaly_reranking_never_changes_bands():
    """Critical guarantee: Isolation Forest only re-ranks within bands; never alters the band."""
    data_path = Path(__file__).resolve().parents[1] / "tools" / "mockgen" / "data" / "mock_features_small.csv"
    if not data_path.exists():
        pytest.skip("mock_features_small.csv not found")

    df = pd.read_csv(data_path)
    scores_no_ml = risk_service.score("case_test", features_df=df, use_anomaly=False)
    scores_with_ml = risk_service.score("case_test", features_df=df, use_anomaly=True)

    band_map_no_ml = {s.entity_id: s.band for s in scores_no_ml}
    band_map_with_ml = {s.entity_id: s.band for s in scores_with_ml}

    for eid in band_map_no_ml:
        assert band_map_no_ml[eid] == band_map_with_ml[eid], (
            f"Entity {eid} band changed from {band_map_no_ml[eid]} to {band_map_with_ml[eid]}!"
        )


def test_graceful_degradation_under_30_entities():
    """Fewer than 30 entities must skip anomaly detection cleanly without crashing."""
    small_df = pd.DataFrame([
        {"entity_id": f"E_{i:02d}", "passthrough_ratio": 0.1 * (i % 10), "total_turnover": 50000.0}
        for i in range(10)
    ])
    scores = risk_service.score("case_small", features_df=small_df, use_anomaly=True)
    assert len(scores) == 10
    # anomaly_used should be 0 because samples < 30
    assert all(s.anomaly_used == 0 for s in scores)
