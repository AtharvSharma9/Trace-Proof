"""
Pramaan S06 — Ingest: Confirm Mapping (views/s06_mapping.py)
Human checkpoint for schema-agnostic header resolution.
Includes confidence bars, match reasons, unmapped columns expander, datetime format check,
10-row preview, disabled Confirm rule with missing fields list, and "Save as reusable format".
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary
from views.components.chips import render_hash_chip
from views.components.banners import render_banner

def render_s06_mapping():
    """Renders S06 Ingest: Confirm Mapping screen."""

    case_id = st.session_state.get("current_case_id", "case_2026_0142")
    file_id = st.query_params.get("file", "ev_001")

    # Fetch file details
    files = api.list_evidence_files(case_id)
    target_file = next((f for f in files if f.id == file_id or f.original_filename == file_id), files[0])

    # Title Block with Back Navigation
    col_back, col_t = st.columns([0.15, 0.85])
    with col_back:
        if btn_secondary("← Back", key="s06_back_btn"):
            st.query_params["view"] = "ingest"
            st.rerun()

    render_screen_title(
        title=f"Confirm Column Mapping — {target_file.original_filename}",
        subtitle="Verify canonical schema interpretation and date formats before parsing into case database.",
        breadcrumbs="Dashboard › Ingestion › Column Mapping"
    )

    # 1. FILE HEADER META CARD
    hash_chip = render_hash_chip(target_file.sha256, status="verified", truncate=False)
    st.markdown(
        f"""
        <div class='tp-card' style='display: flex; justify-content: space-between; align-items: center;'>
            <div>
                <div style='font-family: "JetBrains Mono", monospace; font-size: 16px; font-weight: 700; color: var(--primary);'>{target_file.original_filename}</div>
                <div style='font-size: 13px; color: var(--ink-muted); margin-top: 2px;'>Detected Kind: <b>{target_file.detected_kind}</b> · Size: <b>{target_file.size_bytes / (1024*1024):.1f} MB</b> · Total Rows: <b>{target_file.rows_total:,}</b></div>
            </div>
            <div>
                {hash_chip}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Required Canonical Fields Definition
    REQUIRED_CANONICAL = {
        "CDR": ["caller", "callee", "start_time"],
        "BANK": ["debit_account", "credit_account", "amount", "txn_time"],
        "UPI": ["remitter_vpa", "payee_vpa", "amount", "txn_time"],
        "EML": ["from_address", "to_address", "sent_time"]
    }
    required_fields = REQUIRED_CANONICAL.get(target_file.detected_kind, ["caller", "callee", "start_time"])

    # 2. COLUMN MAPPING TABLE
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Header Resolution & Mapping Table</div>
            <div class='count'>4 required fields</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Mock Detected Mappings for the target file
    mapping_data = [
        {"source": "A-PARTY NO", "samples": "919876543210, 919811122233", "mapped": "caller", "conf": 94, "reason": "'A-PARTY NO' ≈ 'caller' · 94%"},
        {"source": "B-PARTY NO", "samples": "919123456789, 919811144455", "mapped": "callee", "conf": 91, "reason": "'B-PARTY NO' ≈ 'callee' · 91%"},
        {"source": "CALL DATE TIME", "samples": "21/09/2026 14:21:00", "mapped": "start_time", "conf": 98, "reason": "'CALL DATE TIME' ≈ 'start_time' · 98%"},
        {"source": "IMEI NO", "samples": "358941092837412", "mapped": "imei", "conf": 95, "reason": "'IMEI NO' ≈ 'imei' · 95%"},
        {"source": "IMSI NO", "samples": "404450918273645", "mapped": "imsi", "conf": 90, "reason": "'IMSI NO' ≈ 'imsi' · 90%"},
    ]

    canonical_options = ["caller", "callee", "start_time", "duration", "imei", "imsi", "debit_account", "credit_account", "amount", "txn_time", "remitter_vpa", "payee_vpa", "(Ignore Column)"]

    current_mappings = {}

    st.markdown(
        """
        <div style='background: var(--surface-alt); padding: 8px 14px; border: 1px solid var(--border); border-radius: 4px 4px 0 0; font-size: 11.5px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; display: grid; grid-template-columns: 2fr 3fr 2.5fr 1.5fr 3fr; gap: 8px; align-items: center;'>
            <div>Source Column</div>
            <div>Sample Values</div>
            <div>Mapped Canonical Field</div>
            <div>Confidence</div>
            <div>Match Rationale</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for idx, row in enumerate(mapping_data):
        col_m1, col_m2 = st.columns([0.8, 0.2])
        with col_m1:
            st.markdown(
                f"""
                <div style='padding: 8px 14px; border: 1px solid var(--border); border-top: none; font-size: 13px; display: grid; grid-template-columns: 2fr 3fr 2.5fr 1.5fr; gap: 8px; align-items: center;'>
                    <div style='font-family: "JetBrains Mono", monospace; font-weight: 600;'>{row["source"]}</div>
                    <div style='font-size: 12px; color: var(--ink-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{row["samples"]}</div>
                    <div style='font-weight: 600; color: var(--primary);'>{row["mapped"]}</div>
                    <div><span class='tp-risk-chip low'>{row["conf"]}%</span></div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_m2:
            st.selectbox(
                f"Override {row['source']}",
                canonical_options,
                index=canonical_options.index(row["mapped"]) if row["mapped"] in canonical_options else 0,
                key=f"s06_map_select_{idx}",
                label_visibility="collapsed"
            )
            current_mappings[row["source"]] = row["mapped"]

    # Check for missing required fields
    mapped_canonicals = set(current_mappings.values())
    missing_required = [f for f in required_fields if f not in mapped_canonicals]

    # 3. UNMAPPED COLUMNS EXPANDER
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    with st.expander("3 columns ignored (Unmapped source columns)"):
        st.write("• **CELL_ID_FIRST**: `404-20-8912, 404-20-8913` → (Ignored)")
        st.write("• **LAC_CODE**: `8912, 8913` → (Ignored)")
        st.write("• **CALL_TYPE**: `VOICE, VOICE` → (Ignored)")

    # 4. DATETIME FORMAT CHECK
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='tp-card'>
            <div class='tp-h3' style='margin-bottom: 6px;'>Datetime Format Inspection</div>
            <div class='tp-body-sm' style='color: var(--ink-muted); margin-bottom: 10px;'>
                Explicit date format lock avoids day/month swap errors on <code>03/04/2026</code>. All parsed timestamps converted to IST UTC offset.
            </div>
        """,
        unsafe_allow_html=True
    )
    col_dt1, col_dt2 = st.columns(2)
    with col_dt1:
        st.markdown("**Detected Format:** `DD/MM/YYYY HH:mm:ss` (Sample parse: `21 Sep 2026, 14:21:00 IST`)")
    with col_dt2:
        dt_format = st.selectbox(
            "Change Datetime Format",
            ["DD/MM/YYYY HH:mm:ss (Default India)", "YYYY-MM-DD HH:mm:ss (ISO-8601)", "MM/DD/YYYY HH:mm:ss (US)", "DD-MMM-YYYY HH:mm:ss"],
            key="s06_dt_format"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # 5. FIRST 10 NORMALIZED ROWS PREVIEW
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Normalized Data Preview (First 10 Sample Rows)</div>
            <div class='count'>10 sample rows</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    sample_preview = [
        {"caller": "+91 91234 56789", "callee": "+91 98765 43210", "start_time": "21 Sep 2026, 14:21:00 IST", "duration": "240s", "imei": "358941092837412"},
        {"caller": "+91 98765 43210", "callee": "+91 98111 22233", "start_time": "21 Sep 2026, 14:30:00 IST", "duration": "0s (Debit)", "imei": "358941092837412"},
        {"caller": "+91 98111 22233", "callee": "+91 97222 33344", "start_time": "21 Sep 2026, 14:34:00 IST", "duration": "0s (Debit)", "imei": "358941092837412"},
        {"caller": "+91 98111 44455", "callee": "+91 97222 55566", "start_time": "21 Sep 2026, 14:35:00 IST", "duration": "0s (Debit)", "imei": "358941092837412"},
    ]
    st.dataframe(sample_preview, use_container_width=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 6. VALIDATION & DISABLED CONFIRM RULE
    if missing_required:
        render_banner(
            kind="warning",
            title="Required Canonical Fields Missing",
            body=f"Cannot ingest until required fields for {target_file.detected_kind} are mapped: {', '.join(missing_required)}"
        )

    # ACTION BUTTONS
    col_act1, col_act2, col_act3 = st.columns([0.35, 0.45, 0.2])
    with col_act1:
        confirm_disabled = bool(missing_required)
        if btn_primary(
            "Confirm & Ingest File",
            key="s06_confirm_ingest_btn",
            disabled=confirm_disabled,
            help_text="Map all required canonical fields first." if confirm_disabled else None,
            use_container_width=True
        ):
            api.confirm_file_mapping(target_file.id, current_mappings, dt_format)
            st.toast(f"Confirmed mapping for {target_file.original_filename}. Rows parsed!")
            st.query_params["view"] = "ingest"
            st.rerun()

    with col_act2:
        if btn_secondary("💾 Save as Reusable Format Plugin (YAML)", key="s06_save_plugin_btn", use_container_width=True):
            st.toast("Saved mapping as format plugin 'airtel_cdr_v1.yaml'. Future files from this operator will map automatically!")

    with col_act3:
        if btn_secondary("Cancel", key="s06_cancel_btn", use_container_width=True):
            st.query_params["view"] = "ingest"
            st.rerun()
