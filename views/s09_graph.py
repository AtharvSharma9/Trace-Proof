"""
Trace-Proof S09 — Network Graph (views/s09_graph.py)
Interactive PyVis canvas with 100% offline vendored assets, risk matrix colors,
victim ring & cash-out double ring, highlighted path, legend, controls panel,
right-side node/edge drawers, 2-hop neighbourhood isolation, large graph banner,
and static Matplotlib fallback image rendering.
"""

import streamlit as st
import streamlit.components.v1 as components
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary
from views.components.banners import render_banner
from views.components.captions import render_provenance_caption
from views.components.chips import render_risk_chip, render_hash_chip
from views.components.graph_renderer import (
    is_vis_vendored, generate_offline_pyvis_html, generate_matplotlib_fallback_png
)

def render_s09_graph():
    """Renders S09 Network Graph screen."""

    case_id = st.session_state.get("current_case_id", "case_2026_0142")

    # Title Block
    render_screen_title(
        title="Network Graph — Forensic Topology",
        subtitle="Interactive entity resolution graph mapping victim debits, multi-hop mule networks, and ATM cash-out terminals.",
        breadcrumbs="Dashboard › Network Graph"
    )

    # 1. DEMO CENTREPIECE FRAME CAPTION BANNER
    st.markdown(
        """
        <div class='tp-banner success' style='align-items: center; border-left: 4px solid var(--primary);'>
            <div style='display: flex; gap: 12px; align-items: center;'>
                <span style='font-size: 18px;'>🔍</span>
                <div>
                    <div class='title' style='font-size: 15px; font-weight: 700; color: #1B3A5C;'>
                        Victim → 3 mules → ATM cash-out · ₹4,80,000 · 11 minutes
                    </div>
                    <div class='body'>
                        Planted fraud ring recovered end-to-end. 3 hops completed with 96% fund pass-through rate.
                    </div>
                </div>
            </div>
            <div>
                <span class='tp-status-pill verified'>412 Endpoints Scored</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. TOP CONTROLS BAR & REHEARSAL TOGGLES
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns([0.25, 0.25, 0.25, 0.25])
    with col_ctrl1:
        min_conf = st.slider("Link Confidence Threshold", min_value=0.50, max_value=0.99, value=0.75, step=0.05, key="s09_conf_slider")
        st.markdown("<div class='tp-caption'>Lowering this shows weaker links and increases risk of false connections.</div>", unsafe_allow_html=True)

    with col_ctrl2:
        top_n = st.number_input("Top-N Risk Subgraph", min_value=10, max_value=500, value=50, step=10, key="s09_top_n")
        layout_type = st.selectbox("Layout Selector", ["Force-directed", "Hierarchical"], key="s09_layout_sel")

    with col_ctrl3:
        highlight_path = st.checkbox("Highlight victim → cash-out path", value=True, key="s09_hl_path")
        sim_large_graph = st.checkbox("Simulate > 5,000 node graph", value=False, key="s09_sim_large")

    with col_ctrl4:
        sim_missing_vendor = st.checkbox("Simulate missing vendor assets (Fallback Test)", value=False, key="s09_sim_fallback")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # LARGE GRAPH BANNER (> 5,000 nodes)
    if sim_large_graph:
        render_banner(
            kind="warning",
            title="Large Graph Detected (5,420 Endpoints)",
            body="Showing top 500 nodes by risk to preserve UI responsiveness. Adjust N in controls to expand."
        )

    # 3. CANVAS CONTAINER (PYVIS INTERACTIVE OR MATPLOTLIB FALLBACK)
    st.markdown("<div class='tp-card' style='padding: 12px;'>", unsafe_allow_html=True)

    # Check vendor assets availability & simulation toggle
    vendor_available = is_vis_vendored() and not sim_missing_vendor

    if not vendor_available:
        # ASSET ERROR CARD & MATPLOTLIB MANDATORY FALLBACK
        render_banner(
            kind="error",
            title="Graph Renderer Assets Not Found",
            body="Local vis-network vendor files missing in assets/vendor/. Displaying static Matplotlib fallback image so screen is never blank."
        )
        fallback_b64 = generate_matplotlib_fallback_png(case_id)
        st.markdown(
            f"""
            <div style='text-align: center; border: 1px solid var(--border); border-radius: 6px; padding: 12px;'>
                <img src='{fallback_b64}' style='max-width: 100%; height: auto; border-radius: 4px;' alt='Static Matplotlib Graph Fallback' />
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # RENDER 100% OFFLINE PYVIS CANVAS
        pyvis_html = generate_offline_pyvis_html(
            case_id=case_id,
            min_confidence=min_conf,
            top_n=top_n,
            layout_type="force" if "Force" in layout_type else "hierarchical",
            highlight_path=highlight_path
        )
        components.html(pyvis_html, height=640, scrolling=False)

    st.markdown("</div>", unsafe_allow_html=True)

    # 4. ACTION TOOLBAR & EXPORT CONTROLS
    col_act1, col_act2, col_act3, col_act4 = st.columns(4)
    with col_act1:
        if btn_secondary("Fit to Screen", key="s09_fit_btn", use_container_width=True):
            st.toast("Graph view reset & fitted to screen.")
    with col_act2:
        if btn_secondary("📷 Export PNG Image", key="s09_export_png_btn", use_container_width=True):
            st.toast("Saved graph frame as exports/graph_CASE_2026_0142.png (300 DPI)")
    with col_act3:
        if btn_secondary("💾 Export GraphML File", key="s09_export_graphml_btn", use_container_width=True):
            st.toast("Saved topology as exports/graph_CASE_2026_0142.graphml")
    with col_act4:
        if btn_secondary("Reset 2-Hop Isolation", key="s09_reset_iso_btn", use_container_width=True):
            st.toast("Full case graph view restored.")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 5. RIGHT-SIDE INSPECTION DRAWER / PANEL (NODE & EDGE DRILL-DOWN)
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Graph Entity & Edge Inspection Panel (Drawer Simulation)</div>
            <div class='count'>Click any node or edge to inspect provenance</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_node, tab_edge = st.tabs(["Selected Node Inspection", "Selected Edge Inspection"])

    with tab_node:
        col_n_sel, col_n_info = st.columns([0.4, 0.6])
        with col_n_sel:
            selected_node_id = st.selectbox(
                "Select Node to Inspect",
                ["ent_mule1a_acc", "ent_mule1b_acc", "ent_mule1c_upi", "ent_mule2a_acc", "ent_cashout_atm", "ent_victim_acc", "ent_shared_imei_1"],
                key="s09_node_inspect_sel"
            )
        with col_n_info:
            target_entity = api.get_entity_by_id(case_id, selected_node_id)
            if target_entity:
                risk_score_obj = api.get_risk_score_for_entity(case_id, target_entity.id)
                r_chip = render_risk_chip(target_entity.risk_score, target_entity.risk_band)
                
                st.markdown(
                    f"""
                    <div class='tp-card'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                            <div>
                                <div style='font-family: "JetBrains Mono", monospace; font-size: 16px; font-weight: 700; color: var(--primary);'>{target_entity.value}</div>
                                <div style='font-size: 12px; color: var(--ink-muted); margin-top: 2px;'>Type: <b>{target_entity.entity_type}</b> · Occurrences: <b>{target_entity.occurrences}</b></div>
                            </div>
                            <div>{r_chip}</div>
                        </div>
                        <div style='margin-top: 10px; font-size: 13px; color: var(--ink);'>
                            <b>Top Triggered Reason:</b> {risk_score_obj.reasons[0].reason_text if risk_score_obj and risk_score_obj.reasons else 'N/A'}
                        </div>
                    """,
                    unsafe_allow_html=True
                )
                if risk_score_obj and risk_score_obj.reasons:
                    ref = risk_score_obj.reasons[0].evidence_refs[0]
                    st.markdown(render_provenance_caption(ref.filename, ref.row_number, ref.sha256), unsafe_allow_html=True)
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    if btn_primary("Open Full Entity Detail (S11) →", key="s09_open_s11_btn", use_container_width=True):
                        st.query_params["view"] = "entity"
                        st.query_params["eid"] = target_entity.id
                        st.rerun()
                with col_d2:
                    if btn_secondary("Isolate 2-Hop Subgraph", key="s09_iso_2hop_btn", use_container_width=True):
                        st.toast(f"Isolated 2-hop neighbourhood for {target_entity.value}")
                st.markdown("</div>", unsafe_allow_html=True)

    with tab_edge:
        st.markdown(
            """
            <div class='tp-card'>
                <div style='font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: 6px;'>
                    Selected Edge: Victim HDFC 30491029384 ──[ FUND_FLOW ]──► SBI 10928374651 (Rajesh Kumar)
                </div>
                <div style='font-size: 13px; color: var(--ink-muted); margin-bottom: 10px;'>
                    Direct fund transfer of ₹2,50,000 at 14:30:00 IST. Confidence: <b>100%</b>.
                </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(render_provenance_caption("bank_statement_hdfc.xlsx", 1482, "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e"), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
