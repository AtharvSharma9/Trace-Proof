"""
Pramaan S01 — Login Screen (views/s01_login.py)
Full-screen layout (no sidebar).
Includes lockout mechanism with countdown, security rule (never reveal which field failed),
and session-expired banner.
"""

import streamlit as st
import time
from views import api
from views.components.buttons import btn_primary
from views.components.banners import render_banner

def render_s01_login():
    """Renders S01 Login screen."""
    
    # Check if session expired query param or state banner is present
    session_expired = st.session_state.get("session_expired_banner", False) or st.query_params.get("expired") == "1"

    st.markdown(
        """
        <div style='max-width: 480px; margin: 40px auto 16px auto; text-align: center;'>
            <div style='font-size: 32px; font-weight: 700; color: #1B3A5C; letter-spacing: -0.02em;'>Pramaan</div>
            <div style='font-size: 14px; color: #475569; margin-top: 4px;'>Offline Forensic Triage Instrument</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.container():
        st.markdown("<div style='max-width: 440px; margin: 0 auto;' class='tp-card'>", unsafe_allow_html=True)
        
        # Session expired banner
        if session_expired:
            render_banner(
                kind="warning",
                title="Session Expired",
                body="Your session expired. Sign in again."
            )

        st.markdown("<div class='tp-h2' style='margin-bottom: 16px;'>Sign In to Workstation</div>", unsafe_allow_html=True)

        badge_no = st.text_input("Badge Number", placeholder="e.g. BP-94821", key="s01_badge")
        password = st.text_input("Password", type="password", key="s01_pwd")

        # Track failure lockout state
        lockout_key = f"lockout_{badge_no.strip()}"
        lockout_time = st.session_state.get(lockout_key, 0)
        now = time.time()
        
        is_locked = False
        time_remaining = 0
        if lockout_time > now:
            is_locked = True
            time_remaining = int(lockout_time - now)

        if is_locked:
            mins, secs = divmod(time_remaining, 60)
            render_banner(
                kind="error",
                title="Account Temporarily Locked",
                body=f"Locked for 15 minutes after 5 failed attempts. Try again in {mins:02d}:{secs:02d}."
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        submit_clicked = btn_primary("Sign In", key="s01_submit_btn", disabled=is_locked, use_container_width=True)

        if submit_clicked and not is_locked:
            if not badge_no.strip() or not password:
                st.markdown("<div style='color: var(--risk-crit-fill); font-size: 13.5px; margin-top: 8px;'>• Badge number or password is incorrect.</div>", unsafe_allow_html=True)
            else:
                ok, officer, msg = api.authenticate_officer(badge_no.strip(), password)
                if ok and officer:
                    st.session_state["officer"] = officer
                    st.session_state["session_expired_banner"] = False
                    if "expired" in st.query_params:
                        del st.query_params["expired"]
                    st.toast(f"Welcome, {officer.full_name}")
                    st.query_params["view"] = "cases"
                    st.rerun()
                else:
                    # Enforce security rule: NEVER reveal which field was wrong
                    if "5 failed" in msg:
                        st.session_state[lockout_key] = time.time() + 900  # 15 min lock
                        st.rerun()
                    else:
                        st.markdown("<div style='color: var(--risk-crit-fill); font-size: 13.5px; margin-top: 8px;'>• Badge number or password is incorrect.</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style='margin-top: 24px; padding-top: 12px; border-top: 1px solid #E2E8F0; text-align: center; font-size: 11px; color: #94A3B8;'>
                <span class='tp-offline-pill'>Offline · No data leaves this workstation</span>
                <div style='margin-top: 4px;'>Pramaan v1.0.0-offline</div>
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )
