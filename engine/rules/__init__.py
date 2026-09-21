"""
engine/rules/__init__.py
========================
Public interface for the PRAMAAN risk rule engine (R01–R12).
"""

from .config import DEFAULT_CONFIG, compute_weights_hash, load_rules_config
from .evaluator import determine_band, evaluate_entity_features
from .rules import RULE_DISPATCH, RuleResult

__all__ = [
    "load_rules_config",
    "compute_weights_hash",
    "evaluate_entity_features",
    "determine_band",
    "RuleResult",
    "RULE_DISPATCH",
    "DEFAULT_CONFIG",
]
