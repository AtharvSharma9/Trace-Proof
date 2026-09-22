"""
engine/rules/config.py
======================
Loads and validates risk rule weights and thresholds from config/risk_weights.yaml.
Computes deterministic SHA-256 weights_hash for auditability and report generation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import yaml

# Path to default config file
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "risk_weights.yaml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "rules": {
        "R01": {
            "name": "Rapid pass-through",
            "weight": 18.0,
            "threshold": 0.85,
            "window_minutes": 60.0,
            "description": "≥ 85% of credited funds debited within 60 min",
        },
        "R02": {
            "name": "Fan-in",
            "weight": 12.0,
            "threshold": 8.0,
            "window_hours": 2.0,
            "description": "≥ 8 distinct sources crediting within 2 h",
        },
        "R03": {
            "name": "Fan-out",
            "weight": 12.0,
            "threshold": 8.0,
            "window_hours": 2.0,
            "description": "≥ 8 distinct destinations debited within 2 h",
        },
        "R04": {
            "name": "Layering depth",
            "weight": 12.0,
            "threshold": 3.0,
            "window_minutes": 30.0,
            "description": "Sits on a chain of ≥ 3 hops completed in < 30 min",
        },
        "R05": {
            "name": "SIM-switch velocity",
            "weight": 10.0,
            "threshold": 3.0,
            "window_days": 7.0,
            "description": "One IMEI paired with ≥ 3 IMSIs in 7 days",
        },
        "R06": {
            "name": "Device sharing",
            "weight": 8.0,
            "threshold": 3.0,
            "description": "One IMEI used by ≥ 3 distinct phone numbers",
        },
        "R07": {
            "name": "New account, high volume",
            "weight": 10.0,
            "max_age_days": 30.0,
            "min_turnover": 500000.0,
            "description": "Account age < 30 days and turnover > ₹5,00,000",
        },
        "R08": {
            "name": "Cash-out terminal",
            "weight": 14.0,
            "threshold": 1.0,
            "description": "ATM/wallet withdrawal at a chain endpoint",
        },
        "R09": {
            "name": "Spoofed header",
            "weight": 8.0,
            "threshold": 1.0,
            "description": "SPF or DKIM fail, or From != Return-Path",
        },
        "R10": {
            "name": "Odd-hour burst",
            "weight": 5.0,
            "threshold": 5.0,
            "description": "≥ 5 transactions between 00:00 and 05:00 IST",
        },
        "R11": {
            "name": "Call-then-transfer",
            "weight": 12.0,
            "threshold": 1.0,
            "window_minutes": 15.0,
            "description": "Inbound call from an unknown number < 15 min before a victim debit",
        },
        "R12": {
            "name": "Centrality",
            "weight": 10.0,
            "threshold": 0.05,
            "description": "Betweenness in the case's top 5th percentile (≥ 0.05)",
        },
    },
    "bands": {
        "CRITICAL": {"min_score": 80.0, "max_score": 100.0},
        "HIGH": {"min_score": 60.0, "max_score": 79.99},
        "MEDIUM": {"min_score": 30.0, "max_score": 59.99},
        "LOW": {"min_score": 0.0, "max_score": 29.99},
    },
}


def load_rules_config(path: str | Path | None = None) -> Dict[str, Any]:
    """
    Load rules configuration dictionary from YAML file.
    Falls back gracefully to DEFAULT_CONFIG if file is not found.
    """
    cfg_path = Path(path) if path else CONFIG_PATH
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "rules" in data:
                    return data
        except Exception:
            pass
    return DEFAULT_CONFIG


def compute_weights_hash(config: Dict[str, Any] | None = None) -> str:
    """
    Compute canonical SHA-256 hash of the rules config (weights + thresholds).
    Deterministic: sorted keys, compact JSON representation.
    """
    cfg = config if config is not None else load_rules_config()
    canonical_bytes = json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()
