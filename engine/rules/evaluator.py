"""
engine/rules/evaluator.py
=========================
Evaluates rules R01–R12 on entity features, computes composite rule scores,
assigns risk bands (CRITICAL / HIGH / MEDIUM / LOW), and generates RiskReason objects.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from engine.rules.config import load_rules_config
from engine.rules.rules import RULE_DISPATCH, RuleResult

# Safe import from domain.models with local fallback
try:
    from domain.models import RiskReason
except ImportError:
    from pydantic import BaseModel, Field

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


def determine_band(score: float, bands_cfg: Dict[str, Any] | None = None) -> str:
    """
    Map numerical score [0, 100] to a standardized risk band.
    CRITICAL: 80–100, HIGH: 60–79.99, MEDIUM: 30–59.99, LOW: 0–29.99.
    """
    if bands_cfg:
        crit_min = float(bands_cfg.get("CRITICAL", {}).get("min_score", 80.0))
        high_min = float(bands_cfg.get("HIGH", {}).get("min_score", 60.0))
        med_min = float(bands_cfg.get("MEDIUM", {}).get("min_score", 30.0))
    else:
        crit_min, high_min, med_min = 80.0, 60.0, 30.0

    if score >= crit_min:
        return "CRITICAL"
    elif score >= high_min:
        return "HIGH"
    elif score >= med_min:
        return "MEDIUM"
    else:
        return "LOW"


def evaluate_entity_features(
    features: Dict[str, Any],
    risk_score_id: str | None = None,
    config: Dict[str, Any] | None = None,
) -> Tuple[float, str, List[RiskReason], List[RuleResult]]:
    """
    Evaluate all 12 fraud risk rules for a single entity's features.

    Returns:
        (rules_score, band, reasons_list, rule_results_list)
    """
    cfg = config if config is not None else load_rules_config()
    rules_cfg = cfg.get("rules", {})
    bands_cfg = cfg.get("bands", {})
    score_id = risk_score_id or f"rs_{uuid.uuid4().hex[:12]}"

    rule_results: List[RuleResult] = []
    reasons: List[RiskReason] = []
    total_points = 0.0

    # Ensure deterministic ordering R01..R12
    sorted_codes = sorted(RULE_DISPATCH.keys())

    for idx, code in enumerate(sorted_codes, start=1):
        rule_fn = RULE_DISPATCH[code]
        specific_cfg = rules_cfg.get(code, {})
        res = rule_fn(features, specific_cfg)
        rule_results.append(res)
        total_points += res.points_contributed

        # Generate RiskReason model for both triggered and non-triggered rules
        reason = RiskReason(
            id=f"{score_id}_{code}",
            risk_score_id=score_id,
            rule_code=res.rule_code,
            rule_name=res.rule_name,
            triggered=res.triggered,
            raw_value=res.raw_value,
            threshold=res.threshold,
            weight=res.weight,
            points_contributed=res.points_contributed,
            plain_text=res.plain_text,
            display_order=idx,
        )
        reasons.append(reason)

    # Score is capped at 100
    rules_score = round(min(100.0, max(0.0, total_points)), 2)
    band = determine_band(rules_score, bands_cfg)

    return rules_score, band, reasons, rule_results
