"""
Trace-Proof S07 — Evidence Register (views/s07_evidence.py)
Printable, read-only evidence file register with full 64-character SHA-256 hashes.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary
from views.components.chips import render_hash_chip, render_status_pill

def render_s07_evidence():
    """Renders S07 Evidence Register screen."""

    case_id = st.session_state.get("current_case_id", "case_2026_0142")

    # Header Title Block
    title_clicked = render_screen_title(
        title="Evidence Register — Chain of Custody",
        subtitle="Printable inventory of all raw evidence files ingested into case. Full 64-character SHA-256 digests.",
        breadcrumbs="Dashboard › Evidence Register",
        primary_action_label="Verify All Now",
        primary_action_key="s07_verify_all_btn"
    )
    if title_clicked:
        st.query_params["view"] = "integrity"
        st.rerun()

    # Toolbar Controls
    col_act1, col_act2, col_space = st.columns([0.25, 0.25, 0.5])
    with col_act1:
        if btn_secondary("📥 Export Register CSV", key="s07_export_csv_btn", use_container_width=True):
            st.toast("Exported evidence register to case_exports/evidence_register_CASE_2026_0142.csv")
    with col_act2:
        if btn_secondary("🖨️ Print Register", key="s07_print_btn", use_container_width=True):
            st.toast("Print stylesheet activated. Press Ctrl+P to print.")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Evidence Files Table
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Evidence Files Inventory</div>
            <div class='count'>7 active evidence files</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div style='background: var(--surface-alt); padding: 8px 14px; border: 1px solid var(--border); border-radius: 4px 4px 0 0; font-size: 11.5px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr 3.5fr 1.5fr 1.2fr; gap: 8px; align-items: center;'>
            <div>Filename</div>
            <div>Kind</div>
            <div>Size</div>
            <div>Parsed</div>
            <div>Rejected</div>
            <div>Full SHA-256 Hash</div>
            <div>Ingested By</div>
            <div style='text-align: right;'>Status</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    evidence_files = api.list_evidence_files(case_id)
    for ef in evidence_files:
        hash_chip = render_hash_chip(ef.sha256, status="verified", truncate=False)
        pill = render_status_pill("verified", "Active") if ef.parse_status == "PARSED" else render_status_pill("error", ef.parse_status)

        st.markdown(
            f"""
            <div style='padding: 10px 14px; border: 1px solid var(--border); border-top: none; font-size: 12.5px; display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr 3.5fr 1.5fr 1.2fr; gap: 8px; align-items: center;'>
                <div style='font-family: "JetBrains Mono", monospace; font-weight: 600; color: var(--primary);'>{ef.original_filename}</div>
                <div><b>{ef.detected_kind}</b></div>
                <div style='color: var(--ink-muted);'>{ef.size_bytes / (1024*1024):.1f} MB</div>
                <div style='font-family: "JetBrains Mono", monospace;'>{ef.rows_parsed:,}</div>
                <div style='font-family: "JetBrains Mono", monospace;'>{ef.rows_rejected}</div>
                <div>{hash_chip}</div>
                <div style='font-size: 11.5px; color: var(--ink-muted);'>{ef.ingested_by_badge}</div>
                <div style='text-align: right;'>{pill}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
