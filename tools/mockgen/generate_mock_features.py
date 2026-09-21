"""
tools/mockgen/generate_mock_features.py
==========================================
Generates mock feature CSVs to test the IsolationForest anomaly engine.

Produces three datasets:
  1. mock_features_small.csv   — 30  entities  (minimum threshold boundary)
  2. mock_features_medium.csv  — 80  entities  (standard demo dataset)
  3. mock_features_large.csv   — 500 entities  (stress test)

Each dataset contains:
  • Planted mule accounts   — high pass-through, deep layering, elevated centrality
  • Legitimate decoys       — high-fan-in businesses, shared family handsets, CGNAT IPs
  • Innocent baseline       — random low-activity accounts

Run from the project root:
  python tools/mockgen/generate_mock_features.py

Output CSVs go to:  tools/mockgen/data/
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

# ─── Config ───────────────────────────────────────────────────────────────────

SEED = 42
OUTPUT_DIR = Path(__file__).parent / "data"

DATASETS = [
    {"name": "mock_features_small",  "n": 30,  "n_mules": 3,  "n_decoys": 5},
    {"name": "mock_features_medium", "n": 80,  "n_mules": 7,  "n_decoys": 10},
    {"name": "mock_features_large",  "n": 500, "n_mules": 20, "n_decoys": 30},
]


# ─── Generator ────────────────────────────────────────────────────────────────

def generate_dataset(
    n: int,
    n_mules: int,
    n_decoys: int,
    seed: int = SEED,
) -> pd.DataFrame:
    """
    Build a synthetic feature DataFrame.

    Columns match engine/anomaly/isolation_forest.py → FEATURE_COLUMNS
    plus two ground-truth columns:
      entity_type  : MULE | DECOY | INNOCENT
      is_mule      : True/False  (used by accuracy tests, not by the model)
    """
    rng = np.random.default_rng(seed)
    n_innocent = n - n_mules - n_decoys
    assert n_innocent > 0, "n must be larger than n_mules + n_decoys"

    rows = []

    # ── 1. Planted mule accounts ──────────────────────────────────────────────
    for i in range(n_mules):
        rows.append({
            "entity_id":              f"MULE_{i+1:03d}",
            "entity_type":            "MULE",
            "is_mule":                True,

            # Rapid pass-through: 90–99% of credited funds forwarded immediately
            "passthrough_ratio":      rng.uniform(0.90, 0.99),

            # Fan-in from many victims
            "fan_in_count":           int(rng.integers(10, 22)),

            # Fan-out to multiple destinations
            "fan_out_count":          int(rng.integers(8, 16)),

            # Deep layering chain (3–5 hops in <30 min)
            "layering_depth":         int(rng.integers(3, 6)),

            # SIM-switch: one IMEI used with 3–5 different SIMs
            "sim_switch_count":       int(rng.integers(3, 6)),

            # Multiple phones on one device
            "device_share_count":     int(rng.integers(2, 5)),

            # Very new account (1–15 days old)
            "account_age_days":       rng.uniform(1, 15),

            # High turnover — ₹4L to ₹12L
            "total_turnover":         rng.uniform(4_00_000, 12_00_000),

            # Active in odd hours (00:00–05:00 IST)
            "odd_hour_txn_count":     int(rng.integers(5, 16)),

            # High centrality — sits on most victim→cashout paths
            "betweenness_centrality": rng.uniform(0.55, 0.95),
            "pagerank":               rng.uniform(0.05, 0.20),
            "in_degree":              int(rng.integers(10, 20)),
            "out_degree":             int(rng.integers(8, 18)),
            "unique_counterparties":  int(rng.integers(15, 30)),
        })

    # ── 2. Legitimate decoys (should NOT be flagged as mules) ────────────────
    decoy_types = [
        # High fan-in business (petrol pump, kirana store) — high turnover, normal pass-through
        {
            "passthrough_ratio":      rng.uniform(0.02, 0.15),
            "fan_in_count":           int(rng.integers(20, 50)),
            "fan_out_count":          int(rng.integers(1, 4)),
            "layering_depth":         0,
            "sim_switch_count":       0,
            "device_share_count":     1,
            "account_age_days":       rng.uniform(500, 3000),
            "total_turnover":         rng.uniform(5_00_000, 20_00_000),
            "odd_hour_txn_count":     int(rng.integers(0, 2)),
            "betweenness_centrality": rng.uniform(0.0, 0.05),
            "pagerank":               rng.uniform(0.001, 0.005),
            "in_degree":              int(rng.integers(18, 45)),
            "out_degree":             int(rng.integers(1, 4)),
            "unique_counterparties":  int(rng.integers(20, 50)),
        },
        # Family sharing one handset — IMEI shared by 2–3 phones but legitimate
        {
            "passthrough_ratio":      rng.uniform(0.0, 0.10),
            "fan_in_count":           int(rng.integers(1, 5)),
            "fan_out_count":          int(rng.integers(1, 5)),
            "layering_depth":         0,
            "sim_switch_count":       int(rng.integers(2, 4)),   # looks suspicious
            "device_share_count":     int(rng.integers(2, 4)),   # looks suspicious
            "account_age_days":       rng.uniform(200, 2000),
            "total_turnover":         rng.uniform(5_000, 80_000),
            "odd_hour_txn_count":     int(rng.integers(0, 3)),
            "betweenness_centrality": rng.uniform(0.0, 0.03),
            "pagerank":               rng.uniform(0.001, 0.004),
            "in_degree":              int(rng.integers(2, 6)),
            "out_degree":             int(rng.integers(1, 5)),
            "unique_counterparties":  int(rng.integers(3, 10)),
        },
        # CGNAT shared IP — many devices sharing a /24 subnet
        {
            "passthrough_ratio":      rng.uniform(0.0, 0.20),
            "fan_in_count":           int(rng.integers(2, 8)),
            "fan_out_count":          int(rng.integers(1, 6)),
            "layering_depth":         int(rng.integers(0, 2)),
            "sim_switch_count":       0,
            "device_share_count":     1,
            "account_age_days":       rng.uniform(100, 1500),
            "total_turnover":         rng.uniform(10_000, 3_00_000),
            "odd_hour_txn_count":     int(rng.integers(0, 4)),
            "betweenness_centrality": rng.uniform(0.0, 0.06),
            "pagerank":               rng.uniform(0.001, 0.006),
            "in_degree":              int(rng.integers(2, 10)),
            "out_degree":             int(rng.integers(1, 8)),
            "unique_counterparties":  int(rng.integers(3, 15)),
        },
    ]

    for i in range(n_decoys):
        template = decoy_types[i % len(decoy_types)].copy()
        template["entity_id"]   = f"DECOY_{i+1:03d}"
        template["entity_type"] = "DECOY"
        template["is_mule"]     = False
        rows.append(template)

    # ── 3. Innocent baseline ──────────────────────────────────────────────────
    for i in range(n_innocent):
        rows.append({
            "entity_id":              f"INNOCENT_{i+1:04d}",
            "entity_type":            "INNOCENT",
            "is_mule":                False,
            "passthrough_ratio":      rng.uniform(0.0, 0.40),
            "fan_in_count":           int(rng.integers(1, 6)),
            "fan_out_count":          int(rng.integers(1, 6)),
            "layering_depth":         int(rng.integers(0, 2)),
            "sim_switch_count":       int(rng.integers(0, 2)),
            "device_share_count":     int(rng.integers(1, 3)),
            "account_age_days":       rng.uniform(30, 3650),
            "total_turnover":         rng.uniform(1_000, 2_00_000),
            "odd_hour_txn_count":     int(rng.integers(0, 3)),
            "betweenness_centrality": rng.uniform(0.0, 0.08),
            "pagerank":               rng.uniform(0.001, 0.008),
            "in_degree":              int(rng.integers(1, 8)),
            "out_degree":             int(rng.integers(1, 8)),
            "unique_counterparties":  int(rng.integers(1, 12)),
        })

    df = pd.DataFrame(rows)

    # Round floats for readability
    float_cols = [
        "passthrough_ratio", "account_age_days", "total_turnover",
        "betweenness_centrality", "pagerank",
    ]
    df[float_cols] = df[float_cols].round(4)

    return df.reset_index(drop=True)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("PRAMAAN — Mock Feature Dataset Generator")
    print("=" * 50)

    for cfg in DATASETS:
        df = generate_dataset(
            n=cfg["n"],
            n_mules=cfg["n_mules"],
            n_decoys=cfg["n_decoys"],
            seed=SEED,
        )
        out_path = OUTPUT_DIR / f"{cfg['name']}.csv"
        df.to_csv(out_path, index=False)

        mule_count   = df["is_mule"].sum()
        decoy_count  = (df["entity_type"] == "DECOY").sum()
        innoc_count  = (df["entity_type"] == "INNOCENT").sum()

        print(f"\n[{cfg['name']}.csv]")
        print(f"  Total rows   : {len(df)}")
        print(f"  Mules        : {mule_count}")
        print(f"  Decoys       : {decoy_count}")
        print(f"  Innocent     : {innoc_count}")
        print(f"  Saved to     : {out_path}")

    print("\nDone. Load any CSV with pd.read_csv() to test the model.")
    print("Run: python tools/mockgen/test_model_on_mock_data.py")


if __name__ == "__main__":
    main()
