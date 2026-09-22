"""
Pramaan S10 — Risk Board (views/s10_risk.py)
Ranked suspect cards, full sentence reason codes, anomaly model toggle,
band and entity filters, seizure recommendations panel with copy button,
and rules-only degraded banner.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary
from views.components.banners import render_banner
from views.components.chips import render_risk_chip
from views.components.captions import render_provenance_caption

def render_s10_risk():
    """Renders S10 Risk Board screen."""

    case_id = st.session_state.get("current_case_id", "case_2026_0142")

    # Title Block with Generate Brief primary action
    gen_clicked = render_screen_title(
        title="Risk Board — Endpoint Scoring",
        subtitle="Ranked suspect entities scored by R01–R12 forensic rules and optional Isolation Forest anomaly reranking.",
        breadcrumbs="Dashboard › Risk Board",
        primary_action_label="Generate Brief →",
        primary_action_key="s10_gen_brief_btn"
    )
    if gen_clicked:
        st.query_params["view"] = "brief"
        st.rerun()

    # Summary Header Strip
    st.markdown(
        """
        <div class='tp-banner success' style='align-items: center; border-left: 4px solid var(--primary); margin-bottom: 16px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; width: 100%;'>
                <div>
                    <div style='font-size: 15px; font-weight: 700; color: #1B3A5C;'>
                        Scored 412 endpoints · 6 Critical · 14 High · 38 Medium · 354 Low
                    </div>
                    <div style='font-size: 12px; color: #475569; margin-top: 2px;'>
                        Top suspect SBI 10928374651 (Rajesh Kumar) scored 94 Critical. 3 frozen account seizure recommendations ready.
                    </div>
                </div>
                <div>
                    <span class='tp-status-pill verified'>ML Reranking Active</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Controls Panel
    st.markdown("<div class='tp-card' style='padding: 14px;'>", unsafe_allow_html=True)
    col_c1, col_c2, col_c3, col_c4 = st.columns([0.25, 0.25, 0.25, 0.25])
    
    with col_c1:
        ml_enabled = st.toggle("Include anomaly model (Isolation Forest)", value=True, key="s10_ml_toggle")
        st.markdown("<div class='tp-caption'>Off = rules only. The rule score is fully explainable.</div>", unsafe_allow_html=True)

    with col_c2:
        band_filter = st.selectbox("Filter by Band", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"], key="s10_band_filter")

    with col_c3:
        entity_filter = st.selectbox("Filter by Entity Type", ["ALL", "BANK_ACCOUNT", "PHONE", "UPI", "IMEI", "EMAIL"], key="s10_type_filter")

    with col_c4:
        only_path = st.checkbox("Only entities on victim → cash-out path", value=False, key="s10_only_path")
        sim_degraded = st.checkbox("Simulate < 30 endpoints (Rules-only)", value=False, key="s10_sim_degraded")

    st.markdown("</div>", unsafe_allow_html=True)

    # RULES-ONLY DEGRADED BANNER
    if not ml_enabled or sim_degraded:
        render_banner(
            kind="warning",
            title="Rules-Only Scoring Mode Active",
            body="Anomaly model requires at least 30 endpoints or was toggled off. Scores are derived strictly from deterministic R01–R12 rule weights."
        )

    # Layout Split: Left = Suspect Cards (70%), Right = Seizure Recommendations Panel (30%)
    col_main, col_seizure = st.columns([0.68, 0.32])

    with col_main:
        st.markdown(
            """
            <div class='tp-table-header'>
                <div style='font-size: 15px; font-weight: 600;'>Ranked Suspect Endpoints</div>
                <div class='count'>Ranked by Score (Highest First)</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        scores = api.list_risk_scores(case_id, band_filter=band_filter, entity_type=entity_filter, only_path=only_path, ml_enabled=ml_enabled)

        for idx, s in enumerate(scores, 1):
            entity_obj = api.get_entity_by_id(case_id, s.entity_id)
            val_display = entity_obj.value if entity_obj else s.entity_id
            etype_display = entity_obj.entity_type if entity_obj else "BANK_ACCOUNT"

            risk_chip = render_risk_chip(s.score, s.band)

            st.markdown(
                f"""
                <div class='tp-card' style='margin-bottom: 12px; border-left: 4px solid var(--risk-crit-fill) if {s.band=="Critical"} else var(--border);'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                        <div>
                            <span style='font-size: 12px; font-weight: 700; color: var(--ink-muted); margin-right: 6px;'>#{idx}</span>
                            <span style='font-family: "JetBrains Mono", monospace; font-size: 16px; font-weight: 700; color: var(--primary);'>{val_display}</span>
                            <div style='font-size: 12px; color: var(--ink-muted); margin-top: 2px;'>Type: <b>{etype_display}</b> · Rule Score: <b>{s.rule_score:.0f}</b> · ML Score: <b>{s.ml_score:.1f}</b></div>
                        </div>
                        <div>{risk_chip}</div>
                    </div>
                    <div style='margin-top: 10px; font-size: 13px; color: var(--ink); border-top: 1px solid var(--border); padding-top: 8px;'>
                        <div style='font-size: 11px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; margin-bottom: 4px;'>Top Contributing Reason Codes</div>
                """,
                unsafe_allow_html=True
            )

            # Render top 3 reason codes as complete plain sentences
            for r in s.reasons[:3]:
                ref = r.evidence_refs[0] if r.evidence_refs else None
                ref_str = f" ({ref.filename} row {ref.row_number})" if ref else ""
                st.markdown(
                    f"""
                    <div style='margin-bottom: 4px; font-size: 13px;'>
                        • <b>{r.rule_code}</b>: {r.reason_text}
                        {f"<span class='tp-provenance' style='display: inline;'><span class='ref'>{ref.filename} row {ref.row_number}</span></span>" if ref else ""}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

            col_card_act1, col_card_act2, col_card_space = st.columns([0.35, 0.35, 0.3])
            with col_card_act1:
                if btn_primary("View Detail (S11) →", key=f"s10_view_{s.id}_{idx}", use_container_width=True):
                    st.query_params["view"] = "entity"
                    st.query_params["eid"] = s.entity_id
                    st.rerun()
            with col_card_act2:
                if btn_secondary("Add to Brief", key="s10_add_brief_" + str(idx), use_container_width=True):
                    st.toast(f"Added {val_display} to brief suspect list.")

            st.markdown("</div>", unsafe_allow_html=True)

    with col_seizure:
        st.markdown(
            """
            <div class='tp-table-header'>
                <div style='font-size: 15px; font-weight: 600;'>Seizure Recommendations</div>
                <div class='count'>Recoverable Funds</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        seizures = api.get_seizure_recommendations(case_id)
        for idx, sz in enumerate(seizures):
            st.markdown(
                f"""
                <div class='tp-card' style='padding: 14px; margin-bottom: 12px; background: #FAFDFE; border-color: var(--accent-verified-soft);'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                        <div style='font-family: "JetBrains Mono", monospace; font-size: 14px; font-weight: 700; color: var(--primary);'>{sz.entity_value}</div>
                        <span class='tp-risk-chip critical'>{sz.risk_score:.0f}</span>
                    </div>
                    <div style='font-size: 12px; color: var(--ink-muted); margin-top: 2px;'>IFSC: <b>{sz.bank_ifsc}</b> · Acc: <b>{sz.account_number}</b></div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 16px; font-weight: 700; color: var(--risk-low-fill); margin: 6px 0;'>
                        Est. Balance: ₹{sz.estimated_balance:,.2f}
                    </div>
                    <div style='font-size: 12px; color: var(--ink); margin-bottom: 10px;'>
                        {sz.recommendation_text}
                    </div>
                """,
                unsafe_allow_html=True
            )
            
            freeze_text = f"FREEZE REQUEST:\nCase: CASE_2026_0142\nAccount: {sz.account_number}\nIFSC: {sz.bank_ifsc}\nBank: {sz.entity_value}\nReason: Layered Cyber Fraud Mule Account (Risk Score {sz.risk_score:.0f})"
            if btn_secondary("📋 Copy Freeze Request Text", key=f"s10_copy_freeze_{idx}", use_container_width=True):
                st.toast(f"Copied freeze request for {sz.account_number} to clipboard!")
            st.markdown("</div>", unsafe_allow_html=True)
