"""
Trace-Proof Dashboard Metric Tile Component (views/components/tiles.py)
"""

def render_metric_tile(label: str, value: str, subtext: str = "", risk_band: str = None) -> str:
    """
    Renders HTML for a metric tile.
    """
    val_color = "var(--ink)"
    if risk_band:
        b_map = {
            "critical": "var(--risk-crit-fill)",
            "high": "var(--risk-high-fill)",
            "medium": "var(--risk-med-fill)",
            "low": "var(--risk-low-fill)"
        }
        val_color = b_map.get(risk_band.lower(), "var(--ink)")
        
    return f"""
    <div class='tp-metric-tile'>
        <div class='label'>{label}</div>
        <div class='value' style='color: {val_color};'>{value}</div>
        <div class='subtext'>{subtext}</div>
    </div>
    """
