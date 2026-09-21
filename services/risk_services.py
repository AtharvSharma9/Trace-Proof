import sys
from pathlib import Path

# Add project root to path so `engine` module is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.anomaly import run_anomaly_detection, apply_anomaly_reranking
import pandas as pd

# ── Load mock data ──────────────────────────────────────────────────────────
DATA_PATH = "C:/0/Hack/Trace-Proof/tools/mockgen/data/mock_features_large.csv"
features_df = pd.read_csv(DATA_PATH)

# ── Step 1: Run anomaly detection ────────────────────────────────────────────
anomaly_out = run_anomaly_detection(features_df, entity_id_col="entity_id")

# ── Step 2: Build risk_scores_df (simulates what rule engine R01-R12 produces)
# In production this comes from risk_service.score(); here we derive it from features.
risk_scores_df = features_df[["entity_id"]].copy()

risk_scores_df["rules_score"] = (
    features_df["passthrough_ratio"]      * 40 +   # R01 — biggest signal
    features_df["layering_depth"]         * 10 +   # R04
    features_df["fan_in_count"]           *  1.5 + # R02
    features_df["fan_out_count"]          *  1.5 + # R03
    features_df["sim_switch_count"]       *  3 +   # R05
    features_df["betweenness_centrality"] * 10      # R12
).clip(0, 100).round(2)

risk_scores_df["band"] = pd.cut(
    risk_scores_df["rules_score"],
    bins=[-1, 29, 59, 79, 100],
    labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
).astype(str)

# ── Step 3: Re-rank within bands using anomaly scores ───────────────────────
ranked_df = apply_anomaly_reranking(
    risk_scores_df,
    anomaly_out,
    entity_id_col="entity_id",
    score_col="rules_score",
    band_col="band",
)

# ── Print results ────────────────────────────────────────────────────────────
print(f"\nAnomaly detection complete")
print(f"  Entities scored : {anomaly_out.n_samples}")
print(f"  Model version   : {anomaly_out.model_version}")
print(f"  Skipped         : {anomaly_out.skipped}")

print("\nTop 15 entities after anomaly re-ranking:")
print("-" * 65)
print(f"{'Rank':<6} {'Entity ID':<16} {'Band':<10} {'RuleScore':>10} {'AnomalyScore':>13}")
print("-" * 65)
for _, row in ranked_df.head(15).iterrows():
    anom = f"{row['anomaly_score']:.4f}" if row['anomaly_score'] is not None else "N/A"
    print(f"{int(row['final_rank']):<6} {row['entity_id']:<16} {row['band']:<10} "
          f"{row['rules_score']:>10.2f} {anom:>13}")

print("\nBand distribution:")
print(ranked_df["band"].value_counts().to_string())
