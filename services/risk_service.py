from typing import List, Any
from domain.models import RiskScore

def compute_features(g: Any) -> Any:
    """
    Computes a Polars feature DataFrame for each entity in the graph, containing 
    metrics like pass-through ratio, in/out degree, and centrality.
    """
    import polars as pl
    return pl.DataFrame()

def score(case_id: str, use_anomaly: bool = True) -> List[RiskScore]:
    """
    Scores entities using the weighted rules (R01-R12) and optionally an 
    Isolation Forest to re-rank the entities. Generates RiskReason entries.
    """
    return []
