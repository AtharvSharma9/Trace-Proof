"""
Pramaan Screen S17: Synthetic Data Generator & Tamper Simulator (views/s17_mockgen.py)
Rehearsal fixture generator and demo-only tampering simulator.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_header
from views.components.banners import render_status_banner


def render_s17_mockgen():
    case_id = st.session_state.get("current_case_id", "case_2026_0142")
    
    st.markdown(
        render_screen_header(
            title="Mock Data Generator & Rehearsal Sandbox",
            subtitle="Generate synthetic multi-layer cyber-fraud case fixtures or simulate evidence file tampering for demo testing."
        ),
        unsafe_allow_html=True
    )
    
    if "mockgen_msg" in st.session_state:
        st.markdown(render_status_banner("success", st.session_state.pop("mockgen_msg")), unsafe_allow_html=True)
        
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("1. Synthetic Case Generator")
        st.markdown("Configure params to construct a realistic cyber-fraud network with planted victim ring and ATM cash-outs.")
        
        victims = st.number_input("Victim Accounts", min_value=1, max_value=5, value=1, key="mock_victims")
        mule_depth = st.slider("Mule Layer Depth", min_value=1, max_value=4, value=3, key="mock_depth")
        mules_per_layer = st.slider("Mule Accounts per Layer", min_value=2, max_value=5, value=3, key="mock_mules")
        seed = st.number_input("Random Seed (Deterministic)", min_value=1, max_value=9999, value=42, key="mock_seed")
        
        if st.button("Generate & Ingest Synthetic Case Data", type="primary", key="btn_gen_data"):
            api.create_sample_case()
            st.session_state["mockgen_msg"] = f"Generated & loaded Seed {seed} case structure: {victims} victim, {mule_depth}-layer mules, ₹4,80,000 total stolen funds."
            st.rerun()
            
    with c_right:
        st.subheader("2. Demo-Only Tampering Simulator")
        st.markdown("""
        <div style='background: #fff1f2; border: 1px solid #fecdd3; padding: 12px; border-radius: 6px; font-size: 13px; color: #9f1239; margin-bottom: 16px;'>
            <strong>Demonstration Trigger:</strong> Toggling this control simulates silent disk corruption or unauthorized editing of raw evidence files.
        </div>
        """, unsafe_allow_html=True)
        
        # Check current tamper state
        from views.mock import fixtures
        current_tamper = fixtures.is_tampering_simulated()
        
        tamper_checkbox = st.checkbox(
            "Simulate Evidence File Tampering (Demo Only)",
            value=current_tamper,
            key="chk_tamper_sim"
        )
        
        st.caption("When enabled, <code>bank_statement_hdfc.xlsx</code> hash is altered, triggering the full-width red <strong>TAMPER DETECTED</strong> banner on S13.")
        
        if tamper_checkbox != current_tamper:
            api.simulate_tampering(tamper_checkbox)
            state_str = "ENABLED (bank_statement_hdfc.xlsx corrupted)" if tamper_checkbox else "DISABLED (Evidence intact)"
            st.session_state["mockgen_msg"] = f"Tampering simulation is now {state_str}. Visit S13 Integrity Verification to test."
            st.rerun()
            
    st.markdown("<br/><hr style='border: none; border-top: 1px solid var(--border);'><br/>", unsafe_allow_html=True)
    
    st.subheader("Ground Truth Fixture Summary (Seed 42)")
    st.markdown("""
    <div style='background: var(--surface-secondary); padding: 16px; border-radius: 6px; border: 1px solid var(--border); font-size: 13px;'>
        <ul>
            <li><strong>Victim:</strong> SBI 10928374651 (Rajesh Kumar) — Stolen Amount: ₹4,80,000</li>
            <li><strong>Mule Layer 1:</strong> HDFC 9876543210 (Sanjay Shah) & ICICI 5432109876</li>
            <li><strong>Mule Layer 2:</strong> Axis 1122334455 (Vikram Singh)</li>
            <li><strong>Cash-Out Terminal:</strong> ATM-DELHI-SOUTH-04 (Withdrawal ₹4,80,000 in 3 transactions)</li>
            <li><strong>Planted Indicators:</strong> R01 Rapid Pass-Through (< 11 mins), R02 Fan-In (8 CDR logs), R05 SIM Switch (3 IMSIs in 7 days).</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
