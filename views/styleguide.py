"""
Trace-Proof Design System Style Guide View (views/styleguide.py)
Hidden route: ?view=styleguide
Renders every shared component in every state using seed 42 fixtures.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary, render_ghost_button, render_danger_button
from views.components.banners import render_banner
from views.components.chips import render_risk_chip, render_hash_chip, render_status_pill
from views.components.captions import render_provenance_caption, render_table_header_caption
from views.components.tiles import render_metric_tile
from views.components.empty_state import render_empty_state
from views.components.icons import icon_svg

def render_styleguide():
    """Renders comprehensive style guide page."""
    
    # 1. Screen Title Block
    title_clicked = render_screen_title(
        title="Trace-Proof Design System & Style Guide",
        subtitle="Forensic instrument components, typography scale, risk chips, and layout tokens.",
        breadcrumbs="System › Components",
        primary_action_label="+ New Case",
        primary_action_key="sg_primary_top"
    )
    if title_clicked:
        st.toast("Primary action clicked!")

    st.markdown("---")

    # 2. Typography Scale
    st.markdown("### 1. Typography Scale & Fonts")
    st.markdown(
        """
        <div class='tp-card'>
            <div class='tp-display'>Display 30px SemiBold — Case Dashboard Header</div>
            <div class='tp-h1'>H1 24px SemiBold — Section Title / Document Heading</div>
            <div class='tp-h2'>H2 19px SemiBold — Card Title / Panel Header</div>
            <div class='tp-h3'>H3 16px SemiBold — Sub-heading / Group Label</div>
            <div class='tp-body'>Body 15px Regular — Standard UI prose and explanatory notes for investigating officer.</div>
            <div class='tp-body-sm'>Body Small 13.5px Regular — Dense table cells, list metadata, and inline descriptions.</div>
            <div class='tp-caption'>Caption 12px Regular — Timestamps, hints, and provenance metadata.</div>
            <div class='tp-label'>Label 12px Uppercase Tracking — FIELD LABELS & TABLE HEADERS</div>
            <div class='tp-mono'>Monospace 13px Tabular — SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</div>
            <div class='tp-metric'>₹4,80,000.00</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3. Buttons Component Matrix
    st.markdown("### 2. Buttons (Rectangular 6px Radius, Max 1 Primary Per Screen)")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("**Primary (Height 44px)**")
        if btn_primary("Primary Action", key="sg_btn_p"):
            st.toast("Primary clicked")
    with col2:
        st.markdown("**Secondary (Height 38px)**")
        if btn_secondary("Secondary Action", key="sg_btn_s"):
            st.toast("Secondary clicked")
    with col3:
        st.markdown("**Ghost Action**")
        if render_ghost_button("Ghost Action", key="sg_btn_g"):
            st.toast("Ghost clicked")
    with col4:
        st.markdown("**Danger (Red Border)**")
        if render_danger_button("Delete / Exclude", key="sg_btn_d"):
            st.toast("Danger clicked")
    with col5:
        st.markdown("**Disabled State**")
        btn_secondary("Disabled Action", key="sg_btn_dis", disabled=True, help_text="Prerequisite stage incomplete.")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 4. Banners Component Matrix
    st.markdown("### 3. Banners & Inline Alerts")
    render_banner(
        kind="success",
        title="5 evidence files ingested successfully",
        body="Processed 128,430 rows in 6.8 seconds · 18,900 rows/sec · 0 rejected rows.",
        action_label="Go to Correlation",
        action_key="sg_ban_succ"
    )
    render_banner(
        kind="warning",
        title="Not verified since last ingest",
        body="Evidence files were added 14 minutes ago. Run verification before generating brief.",
        action_label="Verify Now",
        action_key="sg_ban_warn"
    )
    render_banner(
        kind="error",
        title="TAMPER DETECTED — Hash Mismatch",
        body="bank_statement_hdfc.xlsx has changed since ingestion (sha256 modified). Brief generation blocked.",
        action_label="View Details",
        action_key="sg_ban_err"
    )
    render_banner(
        kind="info",
        title="Offline Workstation Operating Mode",
        body="Zero network calls detected. All forensic processing executing locally on workstation.",
    )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 5. Risk Scale & Chips Matrix
    st.markdown("### 4. Risk Scale Chips (Score + Word Always Paired)")
    st.markdown(
        f"""
        <div class='tp-card' style='display: flex; gap: 16px; align-items: center;'>
            <div>{render_risk_chip(94.0, "Critical")}</div>
            <div>{render_risk_chip(78.0, "High")}</div>
            <div>{render_risk_chip(45.0, "Medium")}</div>
            <div>{render_risk_chip(22.0, "Low")}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 6. Hash Display & Status Pills
    st.markdown("### 5. Hash Display Chips & Status Pills")
    st.markdown(
        f"""
        <div class='tp-card' style='display: flex; gap: 16px; align-items: center; flex-wrap: wrap;'>
            <div>{render_hash_chip("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", status="verified")}</div>
            <div>{render_hash_chip("ff8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e", status="mismatch")}</div>
            <div>{render_status_pill("verified", "Integrity Verified")}</div>
            <div>{render_status_pill("offline", "Offline · 0 Calls")}</div>
            <div>{render_status_pill("warning", "Stale Verification")}</div>
            <div>{render_status_pill("error", "Tamper Flagged")}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 7. Signature Provenance Caption
    st.markdown("### 6. Signature Provenance Caption (Every Derived Fact Traced)")
    st.markdown(
        f"""
        <div class='tp-card'>
            <div style='font-size: 14px; font-weight: 600;'>Suspect Reason: Forwarded 96% of credited funds within 4 minutes (R01 Rapid pass-through)</div>
            {render_provenance_caption("bank_statement_hdfc.xlsx", 1482, "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e")}
        </div>
        """,
        unsafe_allow_html=True
    )

    # 8. Metric Tiles Matrix
    st.markdown("### 7. Dashboard Metric Tiles")
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.markdown(render_metric_tile("Evidence Files", "7", "128,430 rows ingested"), unsafe_allow_html=True)
    with mcol2:
        st.markdown(render_metric_tile("Entities Extracted", "412", "10 entity types resolved"), unsafe_allow_html=True)
    with mcol3:
        st.markdown(render_metric_tile("Correlated Links", "87", "Min confidence 0.75"), unsafe_allow_html=True)
    with mcol4:
        st.markdown(render_metric_tile("Top Risk Endpoint", "94", "SBI 10928374651", risk_band="critical"), unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 9. Table Caption Header
    st.markdown("### 8. Table Caption Header")
    st.markdown(render_table_header_caption("Evidence File Register", 7, "128,430 total rows"), unsafe_allow_html=True)
    
    # Sample Table
    sample_df = [
        {"Filename": "cdr_operator_airtel.csv", "Kind": "CDR", "Rows": 18450, "Status": "PARSED", "SHA-256": "e3b0c44298fc..."},
        {"Filename": "bank_statement_hdfc.xlsx", "Kind": "BANK", "Rows": 31200, "Status": "PARSED", "SHA-256": "9f8e7d6c5b4a..."},
        {"Filename": "phishing_alert.eml", "Kind": "EML", "Rows": 1, "Status": "PARSED", "SHA-256": "8a7b6c5d4e3f..."}
    ]
    st.dataframe(sample_df, use_container_width=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 10. Empty State Card
    st.markdown("### 9. Empty State Card")
    p_click, s_click = render_empty_state(
        icon_name="database",
        title="No correlation runs executed yet",
        subtext="Run entity resolution and fund flow correlation to populate graph and risk board.",
        action_label="Run Correlation",
        action_key="sg_empty_corr",
        secondary_action_label="Learn more",
        secondary_action_key="sg_empty_info"
    )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 11. Vendored Lucide Icons Grid
    st.markdown("### 10. Vendored Lucide Icons Grid")
    icon_list = ["shield-check", "shield-alert", "check-circle", "alert-triangle", "x-circle", "info", "search", "file-text", "user", "lock", "copy", "external-link", "database", "wifi-off", "chevron-right", "arrow-right"]
    
    ic_html = "<div class='tp-card' style='display: flex; gap: 20px; flex-wrap: wrap; align-items: center;'>"
    for name in icon_list:
        ic_html += f"<div style='text-align: center;'>{icon_svg(name, size=24, color='var(--primary)')}<div style='font-size: 10px; color: var(--ink-muted); margin-top: 4px;'>{name}</div></div>"
    ic_html += "</div>"
    st.markdown(ic_html, unsafe_allow_html=True)
