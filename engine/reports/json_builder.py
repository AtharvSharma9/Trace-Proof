import json
from typing import Dict, List, Any
from pathlib import Path

def build_json_brief(case_data: Dict[str, Any], events: List[Dict[str, Any]], suspects: List[Dict[str, Any]], graph_data: Dict[str, Any], evidence: List[Dict[str, str]], output_path: str) -> None:
    """
    Serializes the exact data state to be printed into a deterministic JSON contract.
    """
    brief_data = {
        "case": case_data,
        "timeline": events,
        "suspects": suspects,
        "graph": graph_data,
        "evidence": evidence
    }
    
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(brief_data, f, indent=2, sort_keys=True)
