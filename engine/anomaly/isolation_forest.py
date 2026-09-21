"""
engine/anomaly/isolation_forest.py
====================================
PRAMAAN — Optional anomaly re-ranking layer.

Role in the pipeline (from 02_TRD.md §3.5 + 06_Implementation_Plan.md Phase 5):
  • Uses scikit-learn IsolationForest on the per-entity feature frame.
  • ONLY re-ranks entities within the same risk band.
  • NEVER changes the band itself (Low / Medium / High / Critical).
  • Can be switched off via a UI toggle — the rule engine must always work alone.
  • Degrades gracefully with a warning when < MIN_SAMPLES entities are available.

Parameters (fixed for reproducibility, printed in the brief):
  n_estimators  = 100
  contamination = "auto"   (tune on synthetic data if desired)
  random_state  = 42       (fixed seed — same inputs → same outputs, always)

Importable by:
  services/risk_service.py → score(case_id, use_anomaly=True)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

#: Minimum number of entities required to fit the model.
#: Below this the model is skipped and rule-only scores are returned unchanged.
MIN_SAMPLES: int = 30

#: IsolationForest hyperparameters — recorded in risk_scores.model_version
N_ESTIMATORS: int = 100
CONTAMINATION: str | float = "auto"
RANDOM_STATE: int = 42

#: Feature columns the model is trained on.
#: Must match the columns produced by risk_service.compute_features().
FEATURE_COLUMNS: list[str] = [
    "passthrough_ratio",      # R01 — fraction of credited funds forwarded out
    "fan_in_count",           # R02 — distinct sources crediting within 2 h
    "fan_out_count",          # R03 — distinct destinations debited within 2 h
    "layering_depth",         # R04 — longest hop chain length
    "sim_switch_count",       # R05 — distinct IMSIs on one IMEI in 7 days
    "device_share_count",     # R06 — distinct phones on one IMEI
    "account_age_days",       # R07 — days since account was opened
    "total_turnover",         # R07 — total credited amount
    "odd_hour_txn_count",     # R10 — transactions between 00:00–05:00 IST
    "betweenness_centrality", # R12 — normalised betweenness in the case graph
    "pagerank",               # supplementary centrality measure
    "in_degree",              # graph degree
    "out_degree",
    "unique_counterparties",  # distinct entities transacted with
]

MODEL_VERSION: str = f"rules-1.0+iforest-{N_ESTIMATORS}est-rs{RANDOM_STATE}"


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class AnomalyResult:
    """Returned for every entity after the model runs."""
    entity_id: str
    anomaly_score: float        # raw IsolationForest score (higher = more anomalous)
    anomaly_rank: int           # rank within the full entity set (1 = most anomalous)
    is_anomaly: bool            # True if the model flagged this entity
    model_version: str = MODEL_VERSION
    random_seed: int = RANDOM_STATE


@dataclass
class AnomalyOutput:
    """Top-level return from run_anomaly_detection()."""
    results: list[AnomalyResult]
    model_version: str = MODEL_VERSION
    random_seed: int = RANDOM_STATE
    n_samples: int = 0
    features_used: list[str] = field(default_factory=list)
    skipped: bool = False           # True when MIN_SAMPLES not met
    skip_reason: Optional[str] = None


# ─── Core function ────────────────────────────────────────────────────────────

def run_anomaly_detection(
    features_df: pd.DataFrame,
    entity_id_col: str = "entity_id",
    contamination: str | float = CONTAMINATION,
    n_estimators: int = N_ESTIMATORS,
    random_state: int = RANDOM_STATE,
) -> AnomalyOutput:
    """
    Fit an IsolationForest on ``features_df`` and return a ranked anomaly result
    for every entity.

    Parameters
    ----------
    features_df : pd.DataFrame
        One row per entity.  Must contain ``entity_id_col`` and all columns in
        ``FEATURE_COLUMNS`` that are available; missing columns are filled with 0.
    entity_id_col : str
        Column name holding the entity identifier.
    contamination, n_estimators, random_state
        Passed directly to sklearn's IsolationForest.

    Returns
    -------
    AnomalyOutput
        Contains one ``AnomalyResult`` per entity, plus metadata.
        If fewer than ``MIN_SAMPLES`` rows are present, ``skipped=True`` and
        the results list is empty — the caller must fall back to rule-only scores.

    Notes
    -----
    • The model is re-fit on every call (never persisted to disk). This keeps
      scores deterministic: same inputs + same seed = same outputs.
    • Features are StandardScaler-normalised before fitting.
    • The IsolationForest ``decision_function`` returns negative scores for
      anomalies; we negate it so higher = more anomalous (easier to reason about).
    """
    n_samples = len(features_df)

    if n_samples < MIN_SAMPLES:
        warn_msg = (
            f"Anomaly model needs at least {MIN_SAMPLES} entities; "
            f"got {n_samples}. Returning rule-based scores only."
        )
        logger.warning(warn_msg)
        return AnomalyOutput(
            results=[],
            n_samples=n_samples,
            skipped=True,
            skip_reason=warn_msg,
        )

    # ── Select and fill features ──────────────────────────────────────────────
    available_cols = [c for c in FEATURE_COLUMNS if c in features_df.columns]
    missing_cols = [c for c in FEATURE_COLUMNS if c not in features_df.columns]
    if missing_cols:
        logger.warning("Missing feature columns (filled with 0): %s", missing_cols)

    X = features_df[available_cols].copy()
    for col in missing_cols:
        X[col] = 0.0
    X = X[FEATURE_COLUMNS]  # enforce consistent column order

    # ── Impute and scale ──────────────────────────────────────────────────────
    X = X.fillna(0.0).replace([np.inf, -np.inf], 0.0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Fit IsolationForest ───────────────────────────────────────────────────
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,          # use all cores; workstation may be 4-core per TRD §8
    )
    model.fit(X_scaled)

    # decision_function: negative = anomalous; negate so higher = more anomalous
    raw_scores: np.ndarray = -model.decision_function(X_scaled)
    predictions: np.ndarray = model.predict(X_scaled)   # -1 = anomaly, 1 = normal

    # ── Build ranked results ──────────────────────────────────────────────────
    entity_ids: list[str] = features_df[entity_id_col].tolist()
    order = np.argsort(raw_scores)[::-1]  # descending: most anomalous first

    results: list[AnomalyResult] = []
    rank_map: dict[int, int] = {idx: rank + 1 for rank, idx in enumerate(order)}

    for i, entity_id in enumerate(entity_ids):
        results.append(
            AnomalyResult(
                entity_id=str(entity_id),
                anomaly_score=float(raw_scores[i]),
                anomaly_rank=rank_map[i],
                is_anomaly=bool(predictions[i] == -1),
            )
        )

    logger.info(
        "IsolationForest fitted on %d entities (%d features). "
        "Flagged %d anomalies.",
        n_samples,
        len(FEATURE_COLUMNS),
        int(np.sum(predictions == -1)),
    )

    return AnomalyOutput(
        results=results,
        n_samples=n_samples,
        features_used=FEATURE_COLUMNS,
        model_version=MODEL_VERSION,
        random_seed=random_state,
    )


# ─── Re-ranking helper (used by risk_service.py) ──────────────────────────────

def apply_anomaly_reranking(
    risk_scores_df: pd.DataFrame,
    anomaly_output: AnomalyOutput,
    entity_id_col: str = "entity_id",
    score_col: str = "rules_score",
    band_col: str = "band",
) -> pd.DataFrame:
    """
    Merge anomaly ranks into the risk score frame and produce a final ordering
    that respects the invariant:

        band ordering is never changed.
        within a band, entities are sorted by (anomaly_rank ASC, rules_score DESC).

    Parameters
    ----------
    risk_scores_df : pd.DataFrame
        Must contain ``entity_id_col``, ``score_col``, and ``band_col``.
    anomaly_output : AnomalyOutput
        Result from ``run_anomaly_detection``.
    Returns
    -------
    pd.DataFrame
        Same rows with an added ``anomaly_score`` column and a ``final_rank``
        column.  Rows are sorted by ``final_rank`` ascending.
    """
    if anomaly_output.skipped or not anomaly_output.results:
        # No anomaly data — rank purely by rules_score within each band
        df = risk_scores_df.copy()
        df["anomaly_score"] = None
        band_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        df["_band_rank"] = df[band_col].map(band_order).fillna(99)
        df = df.sort_values(["_band_rank", score_col], ascending=[True, False])
        df["final_rank"] = range(1, len(df) + 1)
        df.drop(columns=["_band_rank"], inplace=True)
        return df.reset_index(drop=True)

    # Build a lookup: entity_id → (anomaly_score, anomaly_rank)
    anomaly_map: dict[str, tuple[float, int]] = {
        r.entity_id: (r.anomaly_score, r.anomaly_rank)
        for r in anomaly_output.results
    }

    df = risk_scores_df.copy()
    df["anomaly_score"] = df[entity_id_col].map(
        lambda eid: anomaly_map.get(str(eid), (None, None))[0]
    )
    df["anomaly_rank"] = df[entity_id_col].map(
        lambda eid: anomaly_map.get(str(eid), (None, len(df) + 1))[1]
    )

    band_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    df["_band_rank"] = df[band_col].map(band_order).fillna(99)

    # Within a band: anomaly_rank first, then rules_score as tiebreaker
    df = df.sort_values(
        ["_band_rank", "anomaly_rank", score_col],
        ascending=[True, True, False],
    )
    df["final_rank"] = range(1, len(df) + 1)
    df.drop(columns=["_band_rank", "anomaly_rank"], inplace=True)
    return df.reset_index(drop=True)


# ─── Mock data + self-test (run directly: python isolation_forest.py) ─────────

def _make_mock_features(n: int = 80, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """
    Generate synthetic feature data with one planted fraud ring embedded.

    Layout (matches the fraud ring from 06_Implementation_Plan.md Phase 1):
      • Rows 0–6   : planted mules — high pass-through, deep layering, elevated centrality
      • Rows 7–79  : innocent decoys — lower activity, normal distributions
    """
    rng = np.random.default_rng(seed)

    # Innocent baseline
    df = pd.DataFrame({
        "entity_id":             [f"ent_{i:04d}" for i in range(n)],
        "passthrough_ratio":     rng.uniform(0.0, 0.5, n),
        "fan_in_count":          rng.integers(1, 5, n).astype(float),
        "fan_out_count":         rng.integers(1, 5, n).astype(float),
        "layering_depth":        rng.integers(0, 2, n).astype(float),
        "sim_switch_count":      rng.integers(0, 2, n).astype(float),
        "device_share_count":    rng.integers(1, 3, n).astype(float),
        "account_age_days":      rng.uniform(30, 3650, n),
        "total_turnover":        rng.uniform(1_000, 2_00_000, n),
        "odd_hour_txn_count":    rng.integers(0, 3, n).astype(float),
        "betweenness_centrality":rng.uniform(0.0, 0.1, n),
        "pagerank":              rng.uniform(0.001, 0.01, n),
        "in_degree":             rng.integers(1, 8, n).astype(float),
        "out_degree":            rng.integers(1, 8, n).astype(float),
        "unique_counterparties": rng.integers(1, 10, n).astype(float),
        # Ground-truth label (NOT used by model — for evaluation only)
        "is_mule":               [False] * n,
    })

    # Planted mule ring (rows 0–6, clamped to actual df size): override with fraud-like values
    mule_idx = list(range(min(7, n)))
    df.loc[mule_idx, "passthrough_ratio"]      = rng.uniform(0.90, 0.99, len(mule_idx))
    df.loc[mule_idx, "fan_in_count"]           = rng.integers(10, 20, len(mule_idx)).astype(float)
    df.loc[mule_idx, "fan_out_count"]          = rng.integers(8, 15, len(mule_idx)).astype(float)
    df.loc[mule_idx, "layering_depth"]         = rng.integers(3, 5, len(mule_idx)).astype(float)
    df.loc[mule_idx, "sim_switch_count"]       = rng.integers(3, 5, len(mule_idx)).astype(float)
    df.loc[mule_idx, "account_age_days"]       = rng.uniform(1, 15, len(mule_idx))
    df.loc[mule_idx, "total_turnover"]         = rng.uniform(4_00_000, 12_00_000, len(mule_idx))
    df.loc[mule_idx, "odd_hour_txn_count"]     = rng.integers(5, 15, len(mule_idx)).astype(float)
    df.loc[mule_idx, "betweenness_centrality"] = rng.uniform(0.60, 0.95, len(mule_idx))
    df.loc[mule_idx, "is_mule"]               = True

    return df


def _evaluate(df: pd.DataFrame, output: AnomalyOutput) -> None:
    """Print a simple evaluation table against the ground-truth is_mule column."""
    if output.skipped:
        print(f"\n⚠  Model skipped: {output.skip_reason}")
        return

    result_map = {r.entity_id: r for r in output.results}
    rows = []
    for _, row in df.iterrows():
        r = result_map.get(row["entity_id"])
        if r:
            rows.append({
                "entity_id":    row["entity_id"],
                "is_mule":      row["is_mule"],
                "anomaly_score": round(r.anomaly_score, 4),
                "rank":         r.anomaly_rank,
                "flagged":      r.is_anomaly,
            })

    result_df = pd.DataFrame(rows).sort_values("rank")

    # ── Summary stats ──
    mules = result_df[result_df["is_mule"]]
    decoys = result_df[~result_df["is_mule"]]
    flagged_mules  = mules[mules["flagged"]].shape[0]
    flagged_decoys = decoys[decoys["flagged"]].shape[0]

    print("\n-- Top 15 by anomaly rank -----------------------------------------------")
    print(result_df.head(15).to_string(index=False))
    print("\n-- Evaluation Summary ---------------------------------------------------")
    print(f"  Total entities  : {output.n_samples}")
    print(f"  Planted mules   : {mules.shape[0]}")
    print(f"  Mules flagged   : {flagged_mules} / {mules.shape[0]}")
    print(f"  Decoys flagged  : {flagged_decoys} / {decoys.shape[0]}  (false positives)")
    print(f"  Recall          : {flagged_mules / mules.shape[0]:.0%}")
    if (flagged_mules + flagged_decoys) > 0:
        precision = flagged_mules / (flagged_mules + flagged_decoys)
        print(f"  Precision       : {precision:.0%}")
    print(f"  Model version   : {output.model_version}")
    print(f"  Random seed     : {output.random_seed}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    print("=" * 60)
    print("PRAMAAN — IsolationForest anomaly engine (self-test)")
    print("=" * 60)

    mock_df = _make_mock_features(n=80, seed=RANDOM_STATE)
    print(f"\nMock dataset: {len(mock_df)} entities ({mock_df['is_mule'].sum()} planted mules)")

    feature_cols_available = [c for c in FEATURE_COLUMNS if c in mock_df.columns]
    output = run_anomaly_detection(
        features_df=mock_df[["entity_id"] + feature_cols_available],
        entity_id_col="entity_id",
    )

    _evaluate(mock_df, output)

    # ── Test graceful degradation (< MIN_SAMPLES) ──
    print("\n-- Graceful-degradation test (5 entities < 30 minimum) -----------------")
    small_df = _make_mock_features(n=5, seed=RANDOM_STATE)
    small_output = run_anomaly_detection(
        features_df=small_df[["entity_id"] + feature_cols_available],
        entity_id_col="entity_id",
    )
    assert small_output.skipped, "Expected model to skip on small sample"
    print(f"  [OK] Skipped correctly: {small_output.skip_reason}")
    print("\nDone.")
