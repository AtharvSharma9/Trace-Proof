"""
Pramaan S04 — Case Dashboard (views/s04_dashboard.py)
Section 7 of the brief order:
1. Case header
2. Integrity banner
3. Four metric tiles
4. Six-step pipeline strip
5. One primary action whose label follows state
6. Last five audit entries
Includes empty state and failed-run card.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary
from views.components.banners import render_banner
from views.components.tiles import render_metric_tile
from views.components.chips import render_status_pill, render_risk_chip
from views.components.empty_state import render_empty_state
from views.components.icons import icon_svg

def render_s04_dashboard():
    """Renders S04 Case Dashboard screen."""
    
    case_id = st.session_state.get("current_case_id", "case_2026_0142")
    c = api.get_case_by_id(case_id)
    if not c:
        c = api.create_sample_case()
        case_id = c.id

    # Simulated case state controls for demo rehearsal
    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='font-size: 11px; font-weight: 600; color: #94A3B8; text-transform: uppercase;'>Demo State Rehearsal</div>", unsafe_allow_html=True)
    demo_state = st.sidebar.radio(
        "Case State",
        ["Populated Case", "Empty Case (No Evidence)", "Failed Ingest Stage"],
        key="s04_demo_state_radio"
    )

    # 1. CASE HEADER
    st.markdown(
        f"""
        <div style='background: var(--surface-alt); padding: 16px 20px; border: 1px solid var(--border); border-radius: 6px; margin-bottom: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                <div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 14px; font-weight: 700; color: var(--primary);'>
                        {c.case_number} {f"· FIR: {c.fir_number}" if c.fir_number else ""}
                    </div>
                    <div class='tp-h1' style='margin-top: 4px; margin-bottom: 4px;'>{c.title}</div>
                    <div class='tp-body-sm' style='color: var(--ink-muted);'>{c.description}</div>
                </div>
                <div style='text-align: right; font-size: 12px; color: var(--ink-muted);'>
                    <div>Created by <b>{c.created_by_name}</b> ({c.created_by_badge})</div>
                    <div style='margin-top: 2px;'>Station: <b>{c.police_station}</b></div>
                    <div style='margin-top: 2px;'>Opened: <b>{c.created_at}</b></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # EMPTY STATE HANDLING
    if demo_state == "Empty Case (No Evidence)":
        # Render empty pipeline & tiles
        st.markdown(
            f"""
            <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px;'>
                {render_metric_tile("Evidence Files", "0", "0 rows ingested")}
                {render_metric_tile("Entities Extracted", "0", "0 types resolved")}
                {render_metric_tile("Correlated Links", "0", "0 links found")}
                {render_metric_tile("Top Risk Score", "0", "No suspects scored")}
            </div>
            """,
            unsafe_allow_html=True
        )

        p_click, s_click = render_empty_state(
            icon_name="file-text",
            title="No evidence ingested yet",
            subtext="Drop raw evidence files or select a folder path to parse CDR, Bank statements, and UPI records.",
            action_label="Ingest Evidence",
            action_key="s04_empty_ingest_btn",
            secondary_action_label="⚡ Load Seed 42 Demo Evidence",
            secondary_action_key="s04_empty_load_demo"
        )
        if p_click:
            st.query_params["view"] = "ingest"
            st.rerun()
        if s_click:
            st.session_state["s04_demo_state_radio"] = "Populated Case"
            st.rerun()
        return

    # 2. INTEGRITY BANNER
    integ = api.verify_case_integrity(case_id)
    if integ["is_intact"]:
        render_banner(
            kind="success",
            title="All evidence files verified",
            body=f"{integ['message']} · Head Hash: {integ['head_hash'][:16]}…",
            action_label="Verify Integrity Now",
            action_key="s04_verify_now_btn"
        )
    else:
        render_banner(
            kind="error",
            title="TAMPER DETECTED — Hash Mismatch Flagged",
            body=integ["message"],
            action_label="Inspect Integrity Screen",
            action_key="s04_inspect_tamper_btn"
        )

    # FAILED RUN CARD (Conditional)
    if demo_state == "Failed Ingest Stage":
        st.markdown(
            """
            <div class='tp-banner error'>
                <div style='display: flex; gap: 12px; align-items: flex-start;'>
                    <div style='margin-top: 2px;'>❌</div>
                    <div>
                        <div class='title'>Pipeline Failed at Stage: INGEST (bank_statement_corrupt.xlsx)</div>
                        <div class='body'>Polars CSV/XLSX Parser encountered unparseable binary header at offset 0x482. Row 1,412.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        c_retry, c_details = st.columns([0.2, 0.8])
        with c_retry:
            if btn_primary("Retry Ingestion Stage", key="s04_retry_btn"):
                st.session_state["s04_demo_state_radio"] = "Populated Case"
                st.rerun()
        with c_details:
            with st.expander("View Technical Traceback"):
                st.code("Traceback (most recent call last):\n  File 'engine/parsers/bank.py', line 48, in parse_sheet\n    raise InvalidHeaderError('Unparseable binary signature 0x482')\nengine.parsers.bank.InvalidHeaderError: Unparseable binary signature 0x482", language="python")

    # 3. FOUR METRIC TILES
    counts = api.get_case_dashboard_counts(case_id)
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.markdown(render_metric_tile("Evidence", f"{counts['files_count']} files", f"{counts['rows_count']:,} rows parsed"), unsafe_allow_html=True)
    with mcol2:
        st.markdown(render_metric_tile("Entities", f"{counts['entities_count']}", "10 types resolved"), unsafe_allow_html=True)
    with mcol3:
        st.markdown(render_metric_tile("Links", f"{counts['links_count']}", "Min confidence 0.75"), unsafe_allow_html=True)
    with mcol4:
        st.markdown(render_metric_tile("Top Risk", f"{counts['top_risk_score']:.0f}", counts["top_suspect_name"], risk_band=counts["top_risk_band"].lower()), unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 4. SIX-STEP PIPELINE STRIP
    p_status = api.get_pipeline_status(case_id)
    
    def get_pill_html(status_val):
        if status_val == "Done":
            return "<span class='tp-status-pill verified'>✓ Done</span>"
        elif status_val == "In Progress":
            return "<span class='tp-status-pill warning'>⚡ Running</span>"
        elif status_val == "Failed":
            return "<span class='tp-status-pill error'>✗ Failed</span>"
        else:
            return "<span class='tp-status-pill offline'>Pending</span>"

    st.markdown(
        f"""
        <div class='tp-card'>
            <div class='tp-label' style='margin-bottom: 12px;'>6-Stage Evidence Processing Pipeline</div>
            <div style='display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; text-align: center;'>
                <div style='padding: 10px; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: #475569;'>1. INGEST</div>
                    <div style='margin-top: 4px;'>{get_pill_html(p_status.get("Ingest", "Done"))}</div>
                </div>
                <div style='padding: 10px; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: #475569;'>2. HASH</div>
                    <div style='margin-top: 4px;'>{get_pill_html(p_status.get("Hash", "Done"))}</div>
                </div>
                <div style='padding: 10px; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: #475569;'>3. CORRELATE</div>
                    <div style='margin-top: 4px;'>{get_pill_html(p_status.get("Correlate", "Done"))}</div>
                </div>
                <div style='padding: 10px; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: #475569;'>4. GRAPH</div>
                    <div style='margin-top: 4px;'>{get_pill_html(p_status.get("Graph", "Done"))}</div>
                </div>
                <div style='padding: 10px; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: #475569;'>5. SCORE</div>
                    <div style='margin-top: 4px;'>{get_pill_html(p_status.get("Score", "Done"))}</div>
                </div>
                <div style='padding: 10px; background: #FFFFFF; border: 1px solid #1B3A5C; border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: #1B3A5C;'>6. BRIEF</div>
                    <div style='margin-top: 4px;'>{get_pill_html(p_status.get("Brief", "Pending"))}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 5. ONE PRIMARY ACTION (LABEL FOLLOWS CURRENT PIPELINE STATE)
    if counts.get("files_count", 0) == 0 or p_status.get("Ingest") != "Done":
        action_title = "Next Pipeline Stage: Ingest Evidence"
        action_sub = "Drop raw evidence files or folder to begin case triage."
        action_label = "Ingest Evidence →"
        target_view = "ingest"
    elif p_status.get("Correlate") != "Done":
        action_title = "Next Pipeline Stage: Run Correlation"
        action_sub = "Extract entities and discover shared IMEI, IMSI, and beneficiary links."
        action_label = "Run Correlation →"
        target_view = "entities"
    elif p_status.get("Score") != "Done":
        action_title = "Next Pipeline Stage: Run Risk Scoring"
        action_sub = "Rank suspect accounts using R01–R12 weighted rules and anomaly model."
        action_label = "Run Risk Scoring →"
        target_view = "risk"
    else:
        action_title = "Next Pipeline Stage: Generate Court Brief"
        action_sub = "Pipeline complete. All risk reasons verified. Ready to export PDF/JSON brief."
        action_label = "Generate Brief →"
        target_view = "brief"

    st.markdown("<div class='tp-card' style='display: flex; justify-content: space-between; align-items: center;'>", unsafe_allow_html=True)
    col_p_text, col_p_btn = st.columns([0.7, 0.3])
    with col_p_text:
        st.markdown(
            f"""
            <div style='font-size: 15px; font-weight: 600; color: var(--ink);'>{action_title}</div>
            <div style='font-size: 13px; color: var(--ink-muted);'>{action_sub}</div>
            """,
            unsafe_allow_html=True
        )
    with col_p_btn:
        if btn_primary(action_label, key="s04_dynamic_primary_btn", use_container_width=True):
            st.query_params["view"] = target_view
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 6. LAST FIVE AUDIT ENTRIES
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Recent Audit Chain Activity</div>
            <div class='count'>Last 5 audit entries</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    audit_entries = api.list_audit_entries(case_id)[:5]
    audit_rows = []
    for a in audit_entries:
        audit_rows.append({
            "Seq": f"#{a.sequence}",
            "Timestamp": a.timestamp,
            "Officer": f"{a.officer_name} ({a.officer_badge})",
            "Action": a.action,
            "Object": f"{a.object_type}:{a.object_id}",
            "Entry Hash": a.entry_hash[:12] + "…"
        })
    st.dataframe(audit_rows, use_container_width=True)
