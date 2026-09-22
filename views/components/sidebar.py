"""
Trace-Proof Persistent Left Sidebar Shell (views/components/sidebar.py)
Implements fixed 240px shell, pipeline-ordered navigation, disabled state tooltips,
officer info, active case indicator, integrity pill, and offline status footer.
"""

import streamlit as st
from views import api
from views.components.chips import render_status_pill

def render_sidebar(current_view: str, case_id: str) -> str:
    """
    Renders sidebar navigation.
    Returns new view_key if a navigation button was clicked, otherwise returns current_view.
    """
    new_view = current_view

    # Compute pipeline step enablement & tooltips based on active case counts
    counts = api.get_case_dashboard_counts(case_id) if case_id else {}
    pipeline_status = api.get_pipeline_status(case_id) if case_id else {}

    has_evidence = counts.get("files_count", 0) > 0
    has_correlation = counts.get("entities_count", 0) > 0 and pipeline_status.get("Correlate") == "Done"
    has_scores = counts.get("top_risk_score", 0) > 0 and pipeline_status.get("Score") == "Done"

    # Tuple: (Label, ViewKey, Enabled, PrerequisiteTooltip)
    nav_items = [
        ("Dashboard", "dashboard", True, None),
        ("Case List", "cases", True, None),
        ("Ingest Evidence", "ingest", True, None),
        ("Evidence Register", "evidence", has_evidence, "Ingest evidence files first"),
        ("Entities & Links", "entities", has_evidence, "Ingest evidence and run correlation first"),
        ("Network Graph", "graph", has_correlation, "Run entity correlation first to build graph topology"),
        ("Risk Board", "risk", has_correlation, "Run entity correlation and risk scoring first"),
        ("Entity Detail", "entity", has_correlation, "Select an entity from Risk Board or Entities list"),
        ("Timeline", "timeline", has_evidence, "Ingest evidence files first to populate temporal events"),
        ("Integrity Verify", "integrity", has_evidence, "Ingest evidence files first to verify cryptographic hashes"),
        ("Audit Log", "audit", True, None),
        ("Brief Builder", "brief", has_scores, "Score suspect entities and verify integrity before building brief"),
        ("Settings", "settings", True, None),
    ]

    with st.sidebar:
        # 1. Product Header
        st.markdown(
            """
            <div style='padding-bottom: 12px; border-bottom: 1px solid var(--border); margin-bottom: 12px;'>
                <div style='font-size: 18px; font-weight: 700; color: #1B3A5C; letter-spacing: -0.02em;'>
                    Trace-Proof
                </div>
                <div style='font-size: 11px; color: #475569; margin-top: 2px;'>
                    Offline Forensic Triage Instrument
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 2. Active Case Tile
        active_case = api.get_case_by_id(case_id)
        if active_case:
            integ_status = active_case.integrity_status.lower() if hasattr(active_case, "integrity_status") else "verified"
            integ_pill = render_status_pill(integ_status, f"{active_case.integrity_status.title()}")
            
            st.markdown(
                f"""
                <div style='background: #FFFFFF; padding: 10px; border-radius: 6px; border: 1px solid #CBD5E1; margin-bottom: 12px;'>
                    <div style='font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.04em;'>Active Case</div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 13px; font-weight: 700; color: #0F172A; margin-top: 2px;'>{active_case.case_number}</div>
                    <div style='font-size: 12px; color: #1B3A5C; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;'>{active_case.title}</div>
                    <div style='margin-top: 6px;'>
                        {integ_pill}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # 3. Active Officer Info
        officer = st.session_state.get("officer")
        if officer:
            st.markdown(
                f"""
                <div style='font-size: 12px; color: #0F172A; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;'>
                    <div style='font-weight: 600;'>{officer.full_name}</div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 11px; color: #475569;'>{officer.badge_no} · {officer.role}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div style='font-size: 12px; color: #0F172A; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;'>
                    <div style='font-weight: 600;'>Inspector Vikram Singh</div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 11px; color: #475569;'>BP-94821 · SUPERVISOR</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # 4. Pipeline-Ordered Navigation
        st.markdown("<div style='font-size: 11px; font-weight: 600; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px;'>Pipeline Steps</div>", unsafe_allow_html=True)

        for label, view_key, enabled, tooltip in nav_items:
            is_active = (current_view == view_key)
            
            if st.button(
                f"{'• ' if is_active else ''}{label}",
                key=f"sb_nav_{view_key}",
                disabled=not enabled,
                help=tooltip if not enabled else None,
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                new_view = view_key

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # 5. Footer with Offline Pill & Version
        st.markdown(
            """
            <div style='padding-top: 12px; border-top: 1px solid #E2E8F0;'>
                <span class='tp-offline-pill'>Offline · 0 network calls</span>
                <div style='font-size: 10px; color: #94A3B8; margin-top: 6px;'>Trace-Proof v1.0.0-offline</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    return new_view
