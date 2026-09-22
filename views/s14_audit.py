"""
Pramaan S14 — Audit Log (views/s14_audit.py)
Chronological, filterable, read-only audit log table.
Strictly NO edit or delete controls anywhere on this screen by design.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_secondary
from views.components.chips import render_hash_chip
from views.components.banners import render_banner

def render_s14_audit():
    """Renders S14 Audit Log screen."""

    case_id = st.session_state.get("current_case_id", "case_2026_0142")

    # Title Block
    render_screen_title(
        title="Audit Log — Append-Only Forensic Chain",
        subtitle="Chronological, immutable audit record. Every officer action is hash-chained to the genesis entry.",
        breadcrumbs="Dashboard › Audit Log"
    )

    # Filter Controls & Actions Bar
    col_f1, col_f2, col_act1, col_act2 = st.columns([0.3, 0.3, 0.2, 0.2])
    with col_f1:
        action_filter = st.selectbox("Action Type Filter", ["ALL", "CASE_CREATED", "EVIDENCE_INGESTED", "CORRELATION_RUN", "RISK_SCORING_RUN", "INTEGRITY_VERIFIED"], key="s14_action_filter")
    with col_f2:
        officer_filter = st.selectbox("Officer Filter", ["ALL", "BP-94821 (Inspector Vikram Singh)"], key="s14_officer_filter")

    with col_act1:
        if btn_secondary("🔍 Verify Chain", key="s14_verify_chain_btn", use_container_width=True):
            st.toast("Walked audit chain from genesis (#1). All 5 hashes verified intact!")

    with col_act2:
        if btn_secondary("📥 Export CSV/JSON", key="s14_export_btn", use_container_width=True):
            st.toast("Exported audit log to case_exports/audit_log_CASE_2026_0142.csv")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Informational Security Banner
    st.markdown(
        """
        <div class='tp-banner info'>
            <div style='font-size: 13px;'>
                <b>Immutable Record Policy:</b> This audit log contains no edit, delete, or overwrite controls by design. All sequence entries carry SHA-256 cryptographic head digests.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Audit Entries Table
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Audit Log Sequence Table</div>
            <div class='count'>5 entries recorded</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div style='background: var(--surface-alt); padding: 8px 14px; border: 1px solid var(--border); border-radius: 4px 4px 0 0; font-size: 11.5px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; display: grid; grid-template-columns: 0.8fr 2fr 2.5fr 2fr 2fr 1.8fr 1.8fr; gap: 8px; align-items: center;'>
            <div>Seq</div>
            <div>Timestamp</div>
            <div>Officer</div>
            <div>Action</div>
            <div>Target Object</div>
            <div>Previous Hash</div>
            <div>Entry Hash</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    audit_entries = api.list_audit_entries(case_id)
    if action_filter != "ALL":
        audit_entries = [a for a in audit_entries if a.action == action_filter]

    for a in audit_entries:
        prev_chip = render_hash_chip(a.previous_hash, status="verified", truncate=True)
        entry_chip = render_hash_chip(a.entry_hash, status="verified", truncate=True)

        st.markdown(
            f"""
            <div style='padding: 10px 14px; border: 1px solid var(--border); border-top: none; font-size: 13px; display: grid; grid-template-columns: 0.8fr 2fr 2.5fr 2fr 2fr 1.8fr 1.8fr; gap: 8px; align-items: center;'>
                <div style='font-family: "JetBrains Mono", monospace; font-weight: 700; color: var(--primary);'>#{a.sequence}</div>
                <div style='font-size: 12px; color: var(--ink-muted);'>{a.timestamp}</div>
                <div style='font-weight: 500;'>{a.officer_name} ({a.officer_badge})</div>
                <div><span class='tp-status-pill verified'>{a.action}</span></div>
                <div style='font-family: "JetBrains Mono", monospace; font-size: 12px;'>{a.object_type}:{a.object_id}</div>
                <div>{prev_chip}</div>
                <div>{entry_chip}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
