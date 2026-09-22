"""
Pramaan S02 — Case List Screen (views/s02_cases.py)
Renders case registry table with search, status filters, integrity badges,
corrupt case handling, and empty state with sample generator rehearsal shortcut.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary
from views.components.chips import render_status_pill, render_risk_chip
from views.components.empty_state import render_empty_state

def render_s02_cases():
    """Renders S02 Case List screen."""
    
    # Title Block with + New Case primary action
    new_case_clicked = render_screen_title(
        title="Cases",
        subtitle="Select a case file to open dashboard or create a new triage case.",
        primary_action_label="+ New Case",
        primary_action_key="s02_new_case_btn"
    )
    if new_case_clicked:
        st.query_params["view"] = "case_new"
        st.rerun()

    # Search and Filter Controls
    col_search, col_filter, col_corrupt_toggle = st.columns([0.5, 0.3, 0.2])
    with col_search:
        search_q = st.text_input("Search Cases", placeholder="Search by case number, FIR, or title...", key="s02_search", label_visibility="collapsed")
    with col_filter:
        status_f = st.selectbox("Status Filter", ["ALL", "OPEN", "UNDER_REVIEW", "CLOSED"], key="s02_filter", label_visibility="collapsed")
    with col_corrupt_toggle:
        show_corrupt = st.checkbox("Simulate corrupt case", value=False, key="s02_corrupt_demo")

    cases = api.list_cases(search_query=search_q, status_filter=status_f)

    # Empty State check
    if not cases and not show_corrupt:
        p_click, s_click = render_empty_state(
            icon_name="file-text",
            title="No cases yet",
            subtext="Create a case to start triaging evidence, or generate a sample case to rehearse.",
            action_label="+ New Case",
            action_key="s02_empty_new",
            secondary_action_label="⚡ Generate sample case",
            secondary_action_key="s02_empty_sample"
        )
        if p_click:
            st.query_params["view"] = "case_new"
            st.rerun()
        if s_click:
            demo_c = api.create_sample_case()
            st.session_state["current_case_id"] = demo_c.id
            st.toast("Generated sample case CASE_2026_0142!")
            st.query_params["view"] = "dashboard"
            st.query_params["case"] = demo_c.id
            st.rerun()
        return

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Table Header Row
    st.markdown(
        """
        <div style='background: var(--surface-alt); padding: 8px 14px; border: 1px solid var(--border); border-radius: 4px 4px 0 0; font-size: 12px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; display: grid; grid-template-columns: 2fr 3fr 1.5fr 1.5fr 1.2fr 1.5fr 1.5fr 1.5fr; gap: 8px; align-items: center;'>
            <div>Case Number</div>
            <div>Title</div>
            <div>FIR Number</div>
            <div>Created</div>
            <div>Evidence</div>
            <div>Top Risk</div>
            <div>Integrity</div>
            <div style='text-align: right;'>Action</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Table Rows
    for idx, c in enumerate(cases):
        counts = api.get_case_dashboard_counts(c.id)
        integ_kind = c.integrity_status.lower() if hasattr(c, "integrity_status") else "verified"
        integ_pill = render_status_pill(integ_kind, c.integrity_status.title())
        risk_chip = render_risk_chip(counts["top_risk_score"], counts["top_risk_band"])

        col_row, col_act = st.columns([0.88, 0.12])
        with col_row:
            st.markdown(
                f"""
                <div style='padding: 10px 14px; border: 1px solid var(--border); border-top: none; font-size: 13.5px; display: grid; grid-template-columns: 2fr 3fr 1.5fr 1.5fr 1.2fr 1.5fr 1.5fr; gap: 8px; align-items: center;'>
                    <div style='font-family: "JetBrains Mono", monospace; font-weight: 700; color: var(--primary);'>{c.case_number}</div>
                    <div style='font-weight: 500; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{c.title}</div>
                    <div style='color: var(--ink-muted);'>{c.fir_number or "N/A"}</div>
                    <div style='color: var(--ink-muted); font-size: 12px;'>{c.created_at[:11]}</div>
                    <div style='font-family: "JetBrains Mono", monospace;'>{counts["files_count"]} files</div>
                    <div>{risk_chip}</div>
                    <div>{integ_pill}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_act:
            if st.button("Open", key=f"s02_open_{c.id}_{idx}", use_container_width=True):
                st.session_state["current_case_id"] = c.id
                st.query_params["case"] = c.id
                st.query_params["view"] = "dashboard"
                st.rerun()

    # Corrupt Case Demo Row
    if show_corrupt:
        col_c_row, col_c_act = st.columns([0.88, 0.12])
        with col_c_row:
            st.markdown(
                """
                <div style='padding: 10px 14px; border: 1px solid var(--border); border-top: none; font-size: 13.5px; opacity: 0.55; background-color: var(--surface-sunken); display: grid; grid-template-columns: 2fr 3fr 1.5fr 1.5fr 1.2fr 1.5fr 1.5fr; gap: 8px; align-items: center;'>
                    <div style='font-family: "JetBrains Mono", monospace; font-weight: 700; color: var(--ink-muted);'>CASE_2025_0089</div>
                    <div style='font-weight: 500; color: var(--ink-muted);'>[Corrupt SQLite Header] Damaged case database</div>
                    <div>FIR-2025-0012</div>
                    <div style='font-size: 12px;'>10 Aug 2025</div>
                    <div>--</div>
                    <div>--</div>
                    <div><span class='tp-status-pill error' title='Database corrupt: sqlite3.DatabaseError: file is not a database'>✗ Cannot Open</span></div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_c_act:
            st.button("Corrupt", key="s02_corrupt_btn", disabled=True, use_container_width=True, help="Database unreadable. Restore from backup.")
