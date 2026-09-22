"""
Trace-Proof S00 — First-Run Setup Screen (views/s00_setup.py)
Full-screen layout (no sidebar).
Shown when zero officers exist in credential store.
"""

import streamlit as st
import time
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary
from views.components.banners import render_banner

def render_s00_setup():
    """Renders S00 First-Run Setup screen."""
    
    # Check write access simulation / error state
    write_ok = True
    if hasattr(st.session_state, "simulate_write_block") and st.session_state.get("simulate_write_block"):
        write_ok = False

    if not write_ok:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        render_banner(
            kind="error",
            title="Database Not Writable",
            body="Cannot write to the data folder. Run Trace-Proof from a location you have write access to."
        )
        if st.button("Retry Write Access Check"):
            st.session_state["simulate_write_block"] = False
            st.rerun()
        return

    # Header block
    st.markdown(
        """
        <div style='max-width: 600px; margin: 40px auto 20px auto; text-align: center;'>
            <div style='font-size: 28px; font-weight: 700; color: #1B3A5C;'>Trace-Proof</div>
            <div style='font-size: 14px; color: #475569; margin-top: 4px;'>First-Run Setup — Initial Officer Workstation Account</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.container():
        st.markdown("<div style='max-width: 520px; margin: 0 auto;' class='tp-card'>", unsafe_allow_html=True)
        st.markdown("<div class='tp-h2' style='margin-bottom: 16px;'>Create Primary Officer Account</div>", unsafe_allow_html=True)

        full_name = st.text_input("Full Name *", placeholder="e.g. Inspector Vikram Singh", key="s00_name")
        badge_no = st.text_input("Badge Number *", placeholder="e.g. BP-94821", key="s00_badge")
        
        col_r, col_u = st.columns(2)
        with col_r:
            rank = st.selectbox("Rank", ["Inspector of Police", "Sub-Inspector", "Assistant Sub-Inspector", "Deputy Superintendent"], key="s00_rank")
        with col_u:
            unit = st.text_input("Unit / Cyber Cell", value="Cyber Crime Cell, Zone 4", key="s00_unit")

        password = st.text_input("Password (min 10 chars) *", type="password", key="s00_pwd")
        confirm_pwd = st.text_input("Confirm Password *", type="password", key="s00_cpwd")
        is_supervisor = st.checkbox("This is the supervisor account", value=True, key="s00_is_sup")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        if btn_primary("Create Account & Sign In", key="s00_submit_btn", use_container_width=True):
            # Validation checks
            errors = []
            if not full_name.strip():
                errors.append("Full name is required.")
            if not badge_no.strip():
                errors.append("Badge number is required.")
            if len(password) < 10:
                errors.append("Use at least 10 characters for password.")
            if password != confirm_pwd:
                errors.append("Passwords do not match.")

            if errors:
                for err in errors:
                    st.markdown(f"<div style='color: var(--risk-crit-fill); font-size: 13px; margin-bottom: 6px;'>• {err}</div>", unsafe_allow_html=True)
            else:
                role = "SUPERVISOR" if is_supervisor else "ANALYST"
                ok, msg, officer = api.create_officer(
                    badge_no=badge_no.strip(),
                    full_name=full_name.strip(),
                    rank=rank,
                    unit=unit.strip(),
                    role=role,
                    password=password
                )

                if not ok:
                    st.markdown(f"<div style='color: var(--risk-crit-fill); font-size: 13px; margin-bottom: 6px;'>• {msg}</div>", unsafe_allow_html=True)
                else:
                    st.session_state["officer"] = officer
                    st.toast("Account created. You are signed in.")
                    st.query_params["view"] = "cases"
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
