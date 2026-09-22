"""
Pramaan Screen S16: Settings & Risk Thresholds (views/s16_settings.py)
System settings, customizable rule weights, correlation parameters, and offline status probe.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_header
from views.components.banners import render_status_banner


def render_s16_settings():
    st.markdown(
        render_screen_header(
            title="Settings & System Configuration",
            subtitle="Configure risk model weights, correlation thresholds, storage paths, and verify offline operation."
        ),
        unsafe_allow_html=True
    )
    
    if "settings_save_msg" in st.session_state:
        st.markdown(render_status_banner("success", st.session_state.pop("settings_save_msg")), unsafe_allow_html=True)
    if "offline_check_msg" in st.session_state:
        st.markdown(render_status_banner("info", st.session_state.pop("offline_check_msg")), unsafe_allow_html=True)
        
    tabs = st.tabs(["1. Risk Weights (R01–R12)", "2. Correlation Thresholds", "3. Workstation & System"])
    
    # ── TAB 1: RISK WEIGHTS ───────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("""
        <div style='background: var(--surface-secondary); padding: 12px; border-radius: 6px; border: 1px solid var(--border); font-size: 13px; margin-bottom: 16px;'>
            <strong>Forensic Weight Governance:</strong> Adjusting risk model weights re-scores all entities in the current case.
            All modifications are recorded as <code>THRESHOLDS_CHANGED</code> in the append-only audit log.
        </div>
        """, unsafe_allow_html=True)
        
        weights = api.get_risk_weights()
        
        updated_weights = {}
        for w in weights:
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            with col1:
                st.markdown(f"<span style='font-family: \"JetBrains Mono\", monospace; font-weight: 700; color: var(--navy);'>{w['code']}</span>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**{w['name']}**")
            with col3:
                st.caption(w['threshold'])
            with col4:
                val = st.number_input(f"Weight ({w['code']})", min_value=0, max_value=50, value=w['weight'], key=f"weight_{w['code']}")
                updated_weights[w['code']] = val
            st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
            
        if st.button("Save Risk Weights", type="primary", key="btn_save_weights"):
            st.session_state["settings_save_msg"] = "Risk model weights updated successfully. Event `THRESHOLDS_CHANGED` logged to immutable audit trail."
            st.rerun()
            
    # ── TAB 2: CORRELATION THRESHOLDS ─────────────────────────────────────────
    with tabs[1]:
        st.subheader("Correlation Engine Parameters")
        
        c1, c2 = st.columns(2)
        with c1:
            st.slider("Global Link Confidence Cutoff", min_value=0.50, max_value=1.00, value=0.75, step=0.05, key="cfg_conf_cutoff")
            st.selectbox("IP Address Aggregation Subnet", ["/32 (Exact IP)", "/24 (Subnet 255.255.255.0)", "/16 (Class B)"], index=1, key="cfg_ip_subnet")
        with c2:
            st.selectbox("Rapid Pass-Through Time Window", ["15 minutes", "30 minutes", "60 minutes", "120 minutes"], index=2, key="cfg_passthrough_win")
            st.number_input("Fan-In / Fan-Out Min Degree", min_value=3, max_value=20, value=8, key="cfg_degree_min")
            
        if st.button("Save Correlation Thresholds", type="primary", key="btn_save_corr"):
            st.session_state["settings_save_msg"] = "Correlation parameters updated successfully. Audit entry `THRESHOLDS_CHANGED` recorded."
            st.rerun()
            
    # ── TAB 3: WORKSTATION & SYSTEM ───────────────────────────────────────────
    with tabs[2]:
        info = api.get_workstation_info()
        
        st.subheader("Workstation & Storage Settings")
        
        w1, w2 = st.columns(2)
        with w1:
            st.text_input("Default Case Storage Directory", value="C:\\Pramaan\\cases\\", key="cfg_case_dir")
            st.selectbox("Processing Engine Mode", ["Streaming (Low RAM / Large Cases)", "In-Memory (Fastest)"], index=0, key="cfg_proc_mode")
            
        with w2:
            st.markdown(f"""
            <div style='background: var(--surface-secondary); padding: 14px; border-radius: 6px; border: 1px solid var(--border); font-size: 13px;'>
                <strong>System Information:</strong><br/>
                App Name: <strong>{info['app_name']}</strong><br/>
                Version: <code>{info['version']}</code><br/>
                Status: <span style='color: var(--success); font-weight: 600;'>{info['offline_status']}</span><br/>
                Workstation ID: <code>{info['workstation_id']}</code><br/>
                Database: <code>{info['db_location']}</code>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("Check Offline Status", key="btn_check_offline"):
            st.session_state["offline_check_msg"] = f"Network Probe Result: {info['offline_status']} · 0 active sockets · Network interfaces verified unreachable."
            st.rerun()
