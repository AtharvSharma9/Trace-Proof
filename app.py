"""
Pramaan — Offline Forensic Triage Tool
Main Application Router & Session State Manager (app.py)
"""

import streamlit as st
from pathlib import Path
from views import api
from views.components.sidebar import render_sidebar
from views.styleguide import render_styleguide
from views.s00_setup import render_s00_setup
from views.s01_login import render_s01_login
from views.s02_cases import render_s02_cases
from views.s03_case_new import render_s03_case_new
from views.s04_dashboard import render_s04_dashboard
from views.s05_ingest import render_s05_ingest
from views.s06_mapping import render_s06_mapping
from views.s07_evidence import render_s07_evidence
from views.s08_entities import render_s08_entities
from views.s09_graph import render_s09_graph
from views.s10_risk import render_s10_risk
from views.s11_entity import render_s11_entity
from views.s12_timeline import render_s12_timeline
from views.s13_integrity import render_s13_integrity
from views.s14_audit import render_s14_audit
from views.s15_brief import render_s15_brief
from views.s16_settings import render_s16_settings
from views.s17_mockgen import render_s17_mockgen

# ── 1. PAGE CONFIGURATION ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Pramaan — Offline Forensic Triage",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 2. THEME CSS INJECTION ──────────────────────────────────────────────────
def inject_theme():
    css_path = Path(__file__).parent / "assets" / "theme.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

inject_theme()


# ── 3. SESSION & AUTHENTICATION STATE ───────────────────────────────────────
def init_session():
    if "officer" not in st.session_state:
        st.session_state["officer"] = None
    if "current_case_id" not in st.session_state:
        st.session_state["current_case_id"] = "case_2026_0142"

init_session()

# Read query parameters for state persistence
query_params = st.query_params
requested_view = query_params.get("view", "dashboard")
case_id = query_params.get("case", st.session_state.get("current_case_id", "case_2026_0142"))


# ── 4. ROUTER & AUTH GUARD ──────────────────────────────────────────────────
def determine_active_route(requested_view: str) -> str:
    """Enforces section 7 session and redirect rules from App Flow."""
    if requested_view == "styleguide":
        return "styleguide"

    officer_count = api.get_officer_count()
    if officer_count == 0:
        return "setup"

    officer = st.session_state.get("officer")
    if not officer:
        return "login"

    return requested_view


active_view = determine_active_route(requested_view)

# Sync active case ID into session state
if case_id:
    st.session_state["current_case_id"] = case_id


# ── 5. RENDER APPLICATION SHELL & SCREEN ────────────────────────────────────
FULLSCREEN_VIEWS = ["setup", "login", "case_new"]

if active_view in FULLSCREEN_VIEWS:
    if active_view == "setup":
        render_s00_setup()
    elif active_view == "login":
        render_s01_login()
    elif active_view == "case_new":
        render_s03_case_new()

elif active_view == "styleguide":
    new_v = render_sidebar(active_view, case_id)
    if new_v != active_view:
        st.query_params["view"] = new_v
        st.rerun()
    render_styleguide()

else:
    # Screens with persistent sidebar shell
    new_v = render_sidebar(active_view, case_id)
    if new_v != active_view:
        st.query_params["view"] = new_v
        st.rerun()

    if active_view == "cases":
        render_s02_cases()
    elif active_view == "dashboard":
        render_s04_dashboard()
    elif active_view == "ingest":
        render_s05_ingest()
    elif active_view == "mapping":
        render_s06_mapping()
    elif active_view == "evidence":
        render_s07_evidence()
    elif active_view == "entities":
        render_s08_entities()
    elif active_view == "graph":
        render_s09_graph()
    elif active_view == "risk":
        render_s10_risk()
    elif active_view == "entity":
        render_s11_entity()
    elif active_view == "timeline":
        render_s12_timeline()
    elif active_view == "integrity":
        render_s13_integrity()
    elif active_view == "audit":
        render_s14_audit()
    elif active_view == "brief":
        render_s15_brief()
    elif active_view == "settings":
        render_s16_settings()
    elif active_view == "mockgen":
        render_s17_mockgen()
    else:
        # Fallback to dashboard if unrecognized view
        render_s04_dashboard()

