"""
Trace-Proof Screen S08: Entities & Links (views/s08_entities.py)
Entity register and correlated relationship links view.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_header
from views.components.chips import render_risk_chip, render_status_pill
from views.components.banners import render_status_banner
from views.components.captions import render_table_header_caption


def render_s08_entities():
    case_id = st.session_state.get("current_case_id", "case_2026_0142")
    
    st.markdown(
        render_screen_header(
            title="Entities & Links",
            subtitle="Correlated entity registry and relationship link graph"
        ),
        unsafe_allow_html=True
    )
    
    # Audit dismissal state
    if "dismiss_success_msg" in st.session_state:
        st.markdown(render_status_banner("success", st.session_state.pop("dismiss_success_msg")), unsafe_allow_html=True)
    
    tabs = st.tabs(["Entities (412)", "Correlated Links (87)"])
    
    # ── TAB 1: ENTITIES REGISTER ───────────────────────────────────────────────
    with tabs[0]:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_query = st.text_input("Search Entities", placeholder="Search account, IMEI, phone, IP, or name...", key="s08_search")
        with col2:
            type_filter = st.selectbox("Entity Type", ["ALL", "BANK_ACCOUNT", "PHONE_NUMBER", "IMEI", "IP_ADDRESS", "NAME", "ATM_LOCATION"], key="s08_type")
        with col3:
            risk_filter = st.selectbox("Risk Band", ["ALL", "Critical", "High", "Medium", "Low"], key="s08_risk")
            
        entities = api.list_entities(case_id, entity_type=type_filter, search=search_query)
        if risk_filter != "ALL":
            entities = [e for e in entities if e.risk_band.lower() == risk_filter.lower()]
            
        st.markdown(render_table_header_caption("Discovered Entities", len(entities)), unsafe_allow_html=True)
        
        # Display Entity Table
        for e in entities:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 2, 1.5])
                with c1:
                    st.markdown(f"<span style='font-family: \"JetBrains Mono\", monospace; font-weight: 600;'>{e.value}</span>", unsafe_allow_html=True)
                    if e.normalized_value and e.normalized_value != e.value:
                        st.caption(f"Owner/Ref: {e.normalized_value}")
                with c2:
                    st.markdown(f"<span class='tp-badge'>{e.entity_type}</span>", unsafe_allow_html=True)
                with c3:
                    st.markdown(render_risk_chip(e.risk_score, e.risk_band), unsafe_allow_html=True)
                with c4:
                    badges = []
                    if e.is_victim:
                        badges.append("<span style='background: #eff6ff; color: #1d4ed8; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;'>Victim Account</span>")
                    if e.is_cashout:
                        badges.append("<span style='background: #fef2f2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;'>Cash-Out Terminal</span>")
                    if not badges:
                        badges.append("<span style='color: var(--ink-light); font-size: 12px;'>Standard</span>")
                    st.markdown(" ".join(badges), unsafe_allow_html=True)
                with c5:
                    if st.button("View Detail", key=f"view_ent_{e.id}"):
                        st.query_params["view"] = "entity"
                        st.query_params["eid"] = e.id
                        st.rerun()
                st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
                
    # ── TAB 2: CORRELATED LINKS ───────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Confidence Filtering & Link Governance")
        
        col_slider, col_info = st.columns([2, 1])
        with col_slider:
            min_conf = st.slider(
                "Link Confidence Threshold", 
                min_value=0.50, 
                max_value=1.00, 
                value=0.75, 
                step=0.05,
                key="s08_conf_slider"
            )
            st.caption("⚠️ Adjusting confidence changes graph connectivity across all views.")
            
        with col_info:
            st.markdown("""
            <div style='background: var(--surface-secondary); padding: 12px; border-radius: 6px; border: 1px solid var(--border); font-size: 12px;'>
                <strong>Link Audit Policy:</strong><br/>
                Dismissed links are removed from graph analysis but retained in the immutable case log with officer justification.
            </div>
            """, unsafe_allow_html=True)
            
        links = api.list_entity_links(case_id, min_confidence=min_conf)
        st.markdown(render_table_header_caption("Correlated Relationship Links", len(links)), unsafe_allow_html=True)
        
        for link in links:
            with st.container():
                lc1, lc2, lc3, lc4, lc5 = st.columns([2.5, 2, 2.5, 1.5, 1.5])
                with lc1:
                    st.markdown(f"<span style='font-family: \"JetBrains Mono\", monospace; font-size: 13px;'>{link.entity_a_id}</span>", unsafe_allow_html=True)
                with lc2:
                    st.markdown(f"**{link.link_type}**<br/><span style='font-size: 11px; color: var(--ink-light);'>{link.rationale}</span>", unsafe_allow_html=True)
                with lc3:
                    st.markdown(f"<span style='font-family: \"JetBrains Mono\", monospace; font-size: 13px;'>{link.entity_b_id}</span>", unsafe_allow_html=True)
                with lc4:
                    pct = int(link.confidence * 100)
                    st.markdown(f"<span style='font-family: \"JetBrains Mono\", monospace; font-weight: 600; color: var(--navy);'>{pct}% Confidence</span>", unsafe_allow_html=True)
                with lc5:
                    with st.popover("Dismiss link"):
                        st.markdown(f"**Dismiss Link:** `{link.id}`")
                        reason = st.text_input("Dismissal Reason (Required)", key=f"reason_{link.id}")
                        if st.button("Confirm Dismissal", key=f"btn_dismiss_{link.id}", type="primary"):
                            if not reason.strip():
                                st.error("A dismissal reason is mandatory for forensic audit.")
                            else:
                                api.dismiss_link(link.id, reason.strip())
                                st.session_state["dismiss_success_msg"] = f"Link '{link.id}' dismissed successfully. Reason audited: '{reason}'"
                                st.rerun()
                st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
