"""
engine/rules/rules.py
=====================
Pure-function implementations of fraud risk rules R01–R12.
Each rule takes (features: dict, config: dict) and returns a typed RuleResult.
All functions are pure, deterministic, and independently unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RuleResult:
    rule_code: str
    rule_name: str
    triggered: int                     # 1 if rule triggered, 0 otherwise
    raw_value: Optional[float]          # Metric value observed
    threshold: Optional[float]          # Configured threshold
    weight: float                      # Maximum points for this rule
    points_contributed: float          # Points added to total score
    plain_text: str                    # Explanatory sentence for court brief
    evidence_refs: List[str] = field(default_factory=list)  # Associated event/file IDs


# ── R01: Rapid pass-through ──────────────────────────────────────────────────
def evaluate_r01(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R01"
    name = rule_cfg.get("name", "Rapid pass-through")
    weight = float(rule_cfg.get("weight", 18.0))
    threshold = float(rule_cfg.get("threshold", 0.85))
    window_min = float(rule_cfg.get("window_minutes", 60.0))

    raw_val = float(features.get("passthrough_ratio", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"Forwarded {raw_val * 100:.1f}% of credited funds within {window_min:.0f} min "
            f"(R01 Rapid pass-through)"
        )
    else:
        plain_text = (
            f"Pass-through ratio {raw_val * 100:.1f}% below threshold {threshold * 100:.1f}%"
        )

    ev_refs = list(features.get("passthrough_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R01-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=round(raw_val, 4),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R02: Fan-in ──────────────────────────────────────────────────────────────
def evaluate_r02(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R02"
    name = rule_cfg.get("name", "Fan-in")
    weight = float(rule_cfg.get("weight", 12.0))
    threshold = float(rule_cfg.get("threshold", 8.0))
    window_h = float(rule_cfg.get("window_hours", 2.0))

    raw_val = float(features.get("fan_in_count", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"Credited by {int(raw_val)} distinct sources within {window_h:.0f} hours "
            f"(R02 Fan-in)"
        )
    else:
        plain_text = f"Fan-in count {int(raw_val)} below threshold {int(threshold)}"

    ev_refs = list(features.get("fan_in_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R02-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R03: Fan-out ─────────────────────────────────────────────────────────────
def evaluate_r03(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R03"
    name = rule_cfg.get("name", "Fan-out")
    weight = float(rule_cfg.get("weight", 12.0))
    threshold = float(rule_cfg.get("threshold", 8.0))
    window_h = float(rule_cfg.get("window_hours", 2.0))

    raw_val = float(features.get("fan_out_count", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"Debited to {int(raw_val)} distinct destinations within {window_h:.0f} hours "
            f"(R03 Fan-out)"
        )
    else:
        plain_text = f"Fan-out count {int(raw_val)} below threshold {int(threshold)}"

    ev_refs = list(features.get("fan_out_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R03-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R04: Layering depth ──────────────────────────────────────────────────────
def evaluate_r04(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R04"
    name = rule_cfg.get("name", "Layering depth")
    weight = float(rule_cfg.get("weight", 12.0))
    threshold = float(rule_cfg.get("threshold", 3.0))

    raw_val = float(features.get("layering_depth", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"Positioned on a fund transfer chain of depth {int(raw_val)} "
            f"completed in < 30 min (R04 Layering depth)"
        )
    else:
        plain_text = f"Layering depth {int(raw_val)} below threshold {int(threshold)}"

    ev_refs = list(features.get("layering_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R04-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R05: SIM-switch velocity ─────────────────────────────────────────────────
def evaluate_r05(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R05"
    name = rule_cfg.get("name", "SIM-switch velocity")
    weight = float(rule_cfg.get("weight", 10.0))
    threshold = float(rule_cfg.get("threshold", 3.0))
    window_days = float(rule_cfg.get("window_days", 7.0))

    raw_val = float(features.get("sim_switch_count", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"One IMEI paired with {int(raw_val)} distinct IMSIs in {window_days:.0f} days "
            f"(R05 SIM-switch velocity)"
        )
    else:
        plain_text = f"SIM-switch count {int(raw_val)} below threshold {int(threshold)}"

    ev_refs = list(features.get("sim_switch_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R05-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R06: Device sharing ──────────────────────────────────────────────────────
def evaluate_r06(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R06"
    name = rule_cfg.get("name", "Device sharing")
    weight = float(rule_cfg.get("weight", 8.0))
    threshold = float(rule_cfg.get("threshold", 3.0))

    raw_val = float(features.get("device_share_count", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"Device IMEI shared across {int(raw_val)} distinct phone numbers "
            f"(R06 Device sharing)"
        )
    else:
        plain_text = f"Device sharing count {int(raw_val)} below threshold {int(threshold)}"

    ev_refs = list(features.get("device_share_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R06-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R07: New account, high volume ────────────────────────────────────────────
def evaluate_r07(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R07"
    name = rule_cfg.get("name", "New account, high volume")
    weight = float(rule_cfg.get("weight", 10.0))
    max_age = float(rule_cfg.get("max_age_days", 30.0))
    min_turnover = float(rule_cfg.get("min_turnover", 500000.0))

    age = float(features.get("account_age_days", 365.0) or 365.0)
    turnover = float(features.get("total_turnover", 0.0) or 0.0)

    triggered = int(age < max_age and turnover > min_turnover)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"New account ({age:.0f} days old) with high turnover of ₹{turnover:,.2f} "
            f"(R07 New account, high volume)"
        )
    else:
        plain_text = f"Account age {age:.0f} days (limit < {max_age:.0f}d), turnover ₹{turnover:,.2f}"

    ev_refs = list(features.get("account_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R07-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=round(turnover, 2),
        threshold=min_turnover,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R08: Cash-out terminal ───────────────────────────────────────────────────
def evaluate_r08(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R08"
    name = rule_cfg.get("name", "Cash-out terminal")
    weight = float(rule_cfg.get("weight", 14.0))
    threshold = float(rule_cfg.get("threshold", 1.0))

    raw_val = float(
        features.get("cashout_txn_count", 0.0)
        or (1.0 if features.get("is_cashout_terminal") else 0.0)
    )
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            "Terminal cash-out endpoint with ATM/wallet withdrawal activity "
            "(R08 Cash-out terminal)"
        )
    else:
        plain_text = "No terminal cash-out withdrawal detected"

    ev_refs = list(features.get("cashout_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R08-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R09: Spoofed header ──────────────────────────────────────────────────────
def evaluate_r09(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R09"
    name = rule_cfg.get("name", "Spoofed header")
    weight = float(rule_cfg.get("weight", 8.0))
    threshold = float(rule_cfg.get("threshold", 1.0))

    raw_val = float(
        features.get("spoofed_header_count", 0.0)
        or (1.0 if features.get("has_spoofed_header") else 0.0)
    )
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            "Email/SMS header spoofing detected: SPF/DKIM fail or From != Return-Path "
            "(R09 Spoofed header)"
        )
    else:
        plain_text = "No header spoofing or authentication failure detected"

    ev_refs = list(features.get("spoofed_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R09-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R10: Odd-hour burst ──────────────────────────────────────────────────────
def evaluate_r10(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R10"
    name = rule_cfg.get("name", "Odd-hour burst")
    weight = float(rule_cfg.get("weight", 5.0))
    threshold = float(rule_cfg.get("threshold", 5.0))

    raw_val = float(features.get("odd_hour_txn_count", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"{int(raw_val)} transactions recorded during odd night hours 00:00–05:00 IST "
            f"(R10 Odd-hour burst)"
        )
    else:
        plain_text = f"Odd-hour transaction count {int(raw_val)} below threshold {int(threshold)}"

    ev_refs = list(features.get("odd_hour_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R10-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R11: Call-then-transfer ──────────────────────────────────────────────────
def evaluate_r11(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R11"
    name = rule_cfg.get("name", "Call-then-transfer")
    weight = float(rule_cfg.get("weight", 12.0))
    threshold = float(rule_cfg.get("threshold", 1.0))
    window_min = float(rule_cfg.get("window_minutes", 15.0))

    raw_val = float(
        features.get("call_then_transfer_count", 0.0)
        or (1.0 if features.get("has_call_then_transfer") else 0.0)
    )
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"Inbound call from unknown number < {window_min:.0f} min before victim debit "
            f"(R11 Call-then-transfer)"
        )
    else:
        plain_text = "No call-then-transfer sequence detected"

    ev_refs = list(features.get("call_transfer_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R11-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=float(raw_val),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


# ── R12: Centrality ──────────────────────────────────────────────────────────
def evaluate_r12(features: Dict[str, Any], rule_cfg: Dict[str, Any]) -> RuleResult:
    code = "R12"
    name = rule_cfg.get("name", "Centrality")
    weight = float(rule_cfg.get("weight", 10.0))
    threshold = float(rule_cfg.get("threshold", 0.05))

    raw_val = float(features.get("betweenness_centrality", 0.0) or 0.0)
    triggered = int(raw_val >= threshold)
    points = weight if triggered else 0.0

    if triggered:
        plain_text = (
            f"High betweenness centrality ({raw_val:.4f} >= {threshold:.2f}) indicates structural hub "
            f"(R12 Centrality)"
        )
    else:
        plain_text = (
            f"Betweenness centrality ({raw_val:.4f}) below hub threshold ({threshold:.2f})"
        )

    ev_refs = list(features.get("centrality_evidence_refs", []))
    if triggered and not ev_refs and "entity_id" in features:
        ev_refs = [f"REF-R12-{features['entity_id']}"]

    return RuleResult(
        rule_code=code,
        rule_name=name,
        triggered=triggered,
        raw_value=round(raw_val, 4),
        threshold=threshold,
        weight=weight,
        points_contributed=points,
        plain_text=plain_text,
        evidence_refs=ev_refs,
    )


RULE_DISPATCH = {
    "R01": evaluate_r01,
    "R02": evaluate_r02,
    "R03": evaluate_r03,
    "R04": evaluate_r04,
    "R05": evaluate_r05,
    "R06": evaluate_r06,
    "R07": evaluate_r07,
    "R08": evaluate_r08,
    "R09": evaluate_r09,
    "R10": evaluate_r10,
    "R11": evaluate_r11,
    "R12": evaluate_r12,
}
