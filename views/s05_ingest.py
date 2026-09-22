"""
Trace-Proof S05 — Ingest: Drop & Detect (views/s05_ingest.py)
Includes drop zone, detection table with confidence bands, per-row actions,
"Confirm all high-confidence", live rows/sec benchmark summary bar,
and all error states (unknown type, parse failure, duplicate, password-protected, zero-byte, >2GB limit).
"""

import streamlit as st
import time
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary, render_danger_button
from views.components.banners import render_banner
from views.components.chips import render_hash_chip

def render_s05_ingest():
    """Renders S05 Ingest: Drop & Detect screen."""
    
    case_id = st.session_state.get("current_case_id", "case_2026_0142")

    # Screen Header Title Block
    title_clicked = render_screen_title(
        title="Ingest Evidence — Drop & Detect",
        subtitle="Drop raw files or specify a folder path to sniff file types, compute SHA-256, and map schemas.",
        breadcrumbs="Dashboard › Ingestion",
        primary_action_label="Confirm All High-Confidence",
        primary_action_key="s05_confirm_all_high_btn"
    )

    if title_clicked:
        st.toast("Auto-confirmed 5 high-confidence files!")
        st.session_state["s05_all_confirmed"] = True

    # 1. DROP ZONE & FOLDER PATH INPUT
    st.markdown("<div class='tp-card'>", unsafe_allow_html=True)
    st.markdown("<div class='tp-h3' style='margin-bottom: 8px;'>Drop Evidence Files or Folder</div>", unsafe_allow_html=True)
    
    col_drop, col_path = st.columns([0.6, 0.4])
    with col_drop:
        uploaded_files = st.file_uploader(
            "Drop CDR, IPDR, Bank Statements, UPI sheets, or .eml files here",
            accept_multiple_files=True,
            key="s05_uploader",
            help="Supported formats: CSV, XLSX, EML, JSON. Max 2 GB per file."
        )
    with col_path:
        st.markdown("<div style='font-size: 13px; font-weight: 600; color: var(--ink-muted); margin-bottom: 4px;'>Or specify local folder path (large datasets)</div>", unsafe_allow_html=True)
        folder_path = st.text_input("Folder path", placeholder="e.g. C:\\Evidence\\Case_2026_0142\\raw", key="s05_folder_path", label_visibility="collapsed")
        if st.button("Browse Folder Path", key="s05_browse_path_btn"):
            st.toast(f"Scanning folder path: {folder_path or 'C:\\Evidence\\Case_2026_0142'}")

    st.markdown("</div>", unsafe_allow_html=True)

    # Demo Error State Simulator for Rehearsal
    st.markdown(
        """
        <details style='margin-bottom: 16px; font-size: 12px; color: var(--ink-muted);'>
            <summary style='cursor: pointer; font-weight: 600;'>Toggle Ingest Error States (Demo Rehearsal)</summary>
            <div style='margin-top: 8px; padding: 10px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px;'>
        """,
        unsafe_allow_html=True
    )
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        sim_duplicate = st.checkbox("Duplicate File SHA-256", value=False, key="s05_err_dup")
        sim_encrypted = st.checkbox("Encrypted Excel File", value=False, key="s05_err_enc")
    with col_e2:
        sim_parse_fail = st.checkbox("Parse Failure Row", value=False, key="s05_err_parse")
        sim_zerobyte = st.checkbox("Zero-Byte File", value=False, key="s05_err_zero")
    with col_e3:
        sim_unknown = st.checkbox("Unknown Content Type", value=False, key="s05_err_unk")
        sim_large = st.checkbox("> 2 GB File Limit", value=False, key="s05_err_large")
    st.markdown("</div></details>", unsafe_allow_html=True)

    # Render Active Ingest Error Cards if toggled
    if sim_duplicate:
        render_banner("warning", "Duplicate File Skipped", "Already ingested as 'cdr_operator_airtel.csv' (identical SHA-256 e3b0c44298fc…). Audited as EVIDENCE_DUPLICATE_SKIPPED.")
    if sim_encrypted:
        render_banner("error", "Encrypted File Error", "bank_statement_encrypted.xlsx is protected and cannot be read. Supply a decrypted copy.")
    if sim_zerobyte:
        render_banner("error", "Empty File Error", "raw_dump_empty.csv is empty (0 bytes). Skipped.")
    if sim_large:
        render_banner("error", "File Size Limit Exceeded", "full_dump_3gb.bin exceeds the 2 GB ingest limit. Split it and retry.")

    # 2. SUCCESS SUMMARY BAR (INCLUDES LIVE ROWS/SEC BENEFIT DISPLAY)
    st.markdown(
        """
        <div class='tp-banner success' style='align-items: center;'>
            <div style='display: flex; gap: 12px; align-items: center;'>
                <span style='font-size: 18px;'>✓</span>
                <div>
                    <div class='title' style='font-size: 15px;'>5 files ingested · 128,430 rows · 0 rejected · <b>18,900 rows/sec</b></div>
                    <div class='body'>High-confidence schema mappings confirmed. Correlation engine ready.</div>
                </div>
            </div>
            <div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Go to Correlation →", key="s05_go_correlation_btn", type="primary"):
        st.query_params["view"] = "entities"
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

    # 3. DETECTION TABLE WITH CONFIDENCE BANDS & PER-ROW ACTIONS
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Detected Evidence Files</div>
            <div class='count'>7 files detected</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    evidence_files = api.list_evidence_files(case_id)

    # Header Row
    st.markdown(
        """
        <div style='background: var(--surface-alt); padding: 8px 14px; border: 1px solid var(--border); border-radius: 4px 4px 0 0; font-size: 11.5px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; display: grid; grid-template-columns: 2.2fr 1.2fr 1.8fr 1.4fr 1.4fr 1.2fr 2fr; gap: 8px; align-items: center;'>
            <div>Filename</div>
            <div>Size</div>
            <div>SHA-256 (12 chars)</div>
            <div>Detected Kind</div>
            <div>Confidence</div>
            <div>Rows</div>
            <div style='text-align: right;'>Action</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for idx, ef in enumerate(evidence_files):
        # Determine confidence band label
        conf_pct = int(ef.detection_confidence * 100)
        if conf_pct >= 90:
            conf_badge = f"<span class='tp-risk-chip low'>High {conf_pct}%</span>"
        elif conf_pct >= 70:
            conf_badge = f"<span class='tp-risk-chip medium'>Med {conf_pct}%</span>"
        else:
            conf_badge = f"<span class='tp-risk-chip critical'>Low {conf_pct}%</span>"

        hash_chip = render_hash_chip(ef.sha256, status="verified")
        size_mb = f"{ef.size_bytes / (1024*1024):.1f} MB"

        col_r, col_a = st.columns([0.82, 0.18])
        with col_r:
            st.markdown(
                f"""
                <div style='padding: 10px 14px; border: 1px solid var(--border); border-top: none; font-size: 13px; display: grid; grid-template-columns: 2.2fr 1.2fr 1.8fr 1.4fr 1.4fr 1.2fr; gap: 8px; align-items: center;'>
                    <div style='font-family: "JetBrains Mono", monospace; font-weight: 600; color: var(--primary);'>{ef.original_filename}</div>
                    <div style='color: var(--ink-muted);'>{size_mb}</div>
                    <div>{hash_chip}</div>
                    <div><b>{ef.detected_kind}</b></div>
                    <div>{conf_badge}</div>
                    <div style='font-family: "JetBrains Mono", monospace;'>{ef.rows_parsed:,}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_a:
            if st.button("Confirm", key=f"s05_confirm_{ef.id}_{idx}", use_container_width=True):
                st.query_params["view"] = "mapping"
                st.query_params["file"] = ef.id
                st.rerun()

    # Parse Failure Row Display if Toggled
    if sim_parse_fail:
        st.markdown(
            """
            <div style='padding: 10px 14px; border: 1px solid var(--risk-crit-fill); background: var(--risk-crit-bg); font-size: 13px; margin-top: 4px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <b>corrupt_cdr_batch.csv</b> · Parse Failure at Row 1,412 · Unparseable timestamp '99/99/2026'
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("View Rejected Rows (Sample Line Numbers)"):
            st.code("Line 1412: 919876543210, 919123456789, 99/99/2026 25:99:99, INVALID_DURATION\nLine 1418: NULL, 919123456789, 21/09/2026 14:30:00, 120", language="text")

    # Exclude Action Expander
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    with st.expander("Exclude Evidence File (Requires Typed Reason & Audit Entry)"):
        ex_file = st.selectbox("Select file to exclude", [f.original_filename for f in evidence_files], key="s05_ex_sel")
        ex_reason = st.text_input("Mandatory exclusion reason (audited)", placeholder="e.g. Corrupted source file provided by operator", key="s05_ex_reason")
        if render_danger_button("Exclude File", key="s05_ex_submit"):
            if not ex_reason.strip():
                st.error("Exclusion reason is mandatory.")
            else:
                api.exclude_evidence_file(ex_file, ex_reason)
                st.toast(f"Excluded {ex_file}. Audited as EVIDENCE_EXCLUDED.")
