"""
Pramaan Chips & Status Pills (views/components/chips.py)
Includes Risk Chips (score + word), Hash Chips (12-char + copy), and Status Pills.
"""

import streamlit as st
from views.components.icons import icon_svg

def render_risk_chip(score: float, band: str) -> str:
    """
    Renders HTML string for a risk chip.
    Always pairs score and band word together (e.g. '87 Critical').
    """
    b_class = band.lower() if band else "low"
    score_display = f"{score:.0f}" if isinstance(score, (int, float)) else str(score)
    return f"""<span class='tp-risk-chip {b_class}'><span style='font-family: "JetBrains Mono", monospace;'>{score_display}</span> {band}</span>"""

def render_hash_chip(sha256: str, status: str = "verified", truncate: bool = True) -> str:
    """
    Renders HTML string for a SHA-256 hash chip.
    Truncates to 12 chars if requested, full value in tooltip.
    """
    if not sha256:
        return "<span class='tp-hash-chip'>N/A</span>"
    
    display_hash = sha256[:12] + "…" if truncate and len(sha256) > 12 else sha256
    status_class = "verified" if status == "verified" else ("mismatch" if status == "mismatch" else "")
    
    return f"""<span class='tp-hash-chip {status_class}' title='Full SHA-256: {sha256}'>{display_hash}</span>"""

def render_status_pill(kind: str, label: str) -> str:
    """
    Renders HTML string for a status pill.
    kind: 'verified' | 'offline' | 'warning' | 'error'
    """
    ic_map = {
        "verified": icon_svg("shield-check", size=14, color="#0E7C86"),
        "offline": icon_svg("wifi-off", size=14, color="#475569"),
        "warning": icon_svg("alert-triangle", size=14, color="#B45309"),
        "error": icon_svg("shield-alert", size=14, color="#B91C1C")
    }
    ic = ic_map.get(kind, "")
    return f"""<span class='tp-status-pill {kind}'>{ic} {label}</span>"""
