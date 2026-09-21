"""
tools/mockgen/test_model_on_mock_data.py
==========================================
Loads the generated mock CSVs and runs the IsolationForest anomaly engine
against each one. Prints a full evaluation report per dataset.

Run from the project root:
  python tools/mockgen/test_model_on_mock_data.py
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from engine.anomaly import run_anomaly_detection, apply_anomaly_reranking

logging.basicConfig(level=logging.WARNING, format="%(levelname)s  %(message)s")

DATA_DIR = Path(__file__).parent / "data"

CSV_FILES = [
    "mock_features_small.csv",
    "mock_features_medium.csv",
    "mock_features_large.csv",
]


def evaluate(dataset_name: str, df: pd.DataFrame) -> None:
    print(f"\n{'='*60}")
    print(f"  Dataset : {dataset_name}")
    print(f"  Rows    : {len(df)}")
    print(f"  Mules   : {df['is_mule'].sum()} | "
          f"Decoys: {(df['entity_type']=='DECOY').sum()} | "
          f"Innocent: {(df['entity_type']=='INNOCENT').sum()}")
    print(f"{'='*60}")

    # ── Run anomaly detection ────────────────────────────────────────────────
    feature_cols = [
        "passthrough_ratio", "fan_in_count", "fan_out_count",
        "layering_depth", "sim_switch_count", "device_share_count",
        "account_age_days", "total_turnover", "odd_hour_txn_count",
        "betweenness_centrality", "pagerank",
        "in_degree", "out_degree", "unique_counterparties",
    ]
    available = [c for c in feature_cols if c in df.columns]
    output = run_anomaly_detection(
        features_df=df[["entity_id"] + available],
        entity_id_col="entity_id",
    )

    if output.skipped:
        print(f"  [SKIPPED] {output.skip_reason}")
        return

    # ── Merge results with ground truth ─────────────────────────────────────
    result_map = {r.entity_id: r for r in output.results}
    rows = []
    for _, row in df.iterrows():
        r = result_map.get(row["entity_id"])
        if r:
            rows.append({
                "entity_id":    row["entity_id"],
                "entity_type":  row["entity_type"],
                "is_mule":      row["is_mule"],
                "anomaly_score": round(r.anomaly_score, 4),
                "rank":         r.anomaly_rank,
                "flagged":      r.is_anomaly,
            })

    result_df = pd.DataFrame(rows).sort_values("rank").reset_index(drop=True)

    # ── Top 10 by rank ────────────────────────────────────────────────────────
    print("\n  Top 10 entities by anomaly rank:")
    print("  " + "-" * 70)
    header = f"  {'Rank':<6} {'Entity ID':<16} {'Type':<10} {'Score':>8}  {'Mule?':<6} {'Flagged'}"
    print(header)
    print("  " + "-" * 70)
    for _, r in result_df.head(10).iterrows():
        mule_marker = "***" if r["is_mule"] else ""
        print(f"  {int(r['rank']):<6} {r['entity_id']:<16} {r['entity_type']:<10} "
              f"{r['anomaly_score']:>8.4f}  {mule_marker:<6} {r['flagged']}")

    # ── Accuracy metrics ──────────────────────────────────────────────────────
    mules   = result_df[result_df["is_mule"]]
    decoys  = result_df[result_df["entity_type"] == "DECOY"]
    innoc   = result_df[result_df["entity_type"] == "INNOCENT"]

    flagged_mules    = mules[mules["flagged"]].shape[0]
    flagged_decoys   = decoys[decoys["flagged"]].shape[0]
    flagged_innocent = innoc[innoc["flagged"]].shape[0]
    total_flagged    = result_df["flagged"].sum()

    recall    = flagged_mules / max(mules.shape[0], 1)
    precision = flagged_mules / max(total_flagged, 1)
    f1        = (2 * precision * recall) / max(precision + recall, 1e-9)

    print(f"\n  Accuracy Summary:")
    print(f"  {'Mules detected':<28}: {flagged_mules} / {mules.shape[0]}")
    print(f"  {'Decoys falsely flagged':<28}: {flagged_decoys} / {decoys.shape[0]}")
    print(f"  {'Innocent falsely flagged':<28}: {flagged_innocent} / {innoc.shape[0]}")
    print(f"  {'Recall':<28}: {recall:.0%}")
    print(f"  {'Precision':<28}: {precision:.0%}")
    print(f"  {'F1 Score':<28}: {f1:.2f}")
    print(f"  {'Model version':<28}: {output.model_version}")

    # ── Re-ranking test ──────────────────────────────────────────────────────
    # Simulate a risk_scores_df as if the rule engine ran
    risk_scores_df = df[["entity_id"]].copy()
    risk_scores_df["rules_score"] = (
        df["passthrough_ratio"] * 40 +
        df["layering_depth"] * 10 +
        df["fan_in_count"] * 1.5
    ).clip(0, 100)
    risk_scores_df["band"] = pd.cut(
        risk_scores_df["rules_score"],
        bins=[-1, 29, 59, 79, 100],
        labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    ).astype(str)

    ranked = apply_anomaly_reranking(risk_scores_df, output)
    top5   = ranked.head(5)

    print(f"\n  After re-ranking (top 5):")
    print("  " + "-" * 55)
    for _, r in top5.iterrows():
        entity_type = df.loc[df["entity_id"] == r["entity_id"], "entity_type"].values
        etype = entity_type[0] if len(entity_type) else "?"
        print(f"  Rank {int(r['final_rank']):<4} | {r['entity_id']:<16} | "
              f"Band: {r['band']:<8} | RuleScore: {r['rules_score']:.1f} | Type: {etype}")


def main() -> None:
    print("PRAMAAN — IsolationForest Test Runner")
    print("Loading mock datasets from:", DATA_DIR)

    if not DATA_DIR.exists():
        print("\n[ERROR] Data directory not found.")
        print("Run this first:  python tools/mockgen/generate_mock_features.py")
        sys.exit(1)

    found = False
    for csv_name in CSV_FILES:
        csv_path = DATA_DIR / csv_name
        if not csv_path.exists():
            print(f"\n[SKIP] {csv_name} not found — run generate_mock_features.py first.")
            continue
        found = True
        df = pd.read_csv(csv_path)
        evaluate(csv_name, df)

    if not found:
        print("\n[ERROR] No CSV files found. Run generate_mock_features.py first.")
        sys.exit(1)

    print("\n\nAll datasets tested.")


if __name__ == "__main__":
    main()
