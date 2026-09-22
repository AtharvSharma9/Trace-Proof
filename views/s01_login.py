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
    """Renders S01 Login screen with split-screen hero showcase and interactive credentials selector."""
    
    # Check if session expired query param or state banner is present
    session_expired = st.session_state.get("session_expired_banner", False) or st.query_params.get("expired") == "1"

    # Outer padding space
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    col_hero, col_form = st.columns([1.1, 1], gap="large")

    with col_hero:
        st.markdown(
            """<div style='background: linear-gradient(135deg, #0F172A 0%, #1B3A5C 100%); color: white; padding: 32px; border-radius: 14px; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.15); min-height: 480px; display: flex; flex-direction: column; justify-content: space-between;'>
<div>
<div style='display: inline-flex; align-items: center; gap: 8px; background: rgba(14, 124, 134, 0.25); border: 1px solid rgba(14, 124, 134, 0.5); color: #2DD4BF; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 5px 14px; border-radius: 20px; margin-bottom: 24px;'>
<span>🟢</span> AIR-GAPPED WORKSTATION ONLINE
</div>
<div style='display: flex; align-items: center; gap: 12px; margin-bottom: 8px;'>
<span style='font-size: 38px;'>🛡️</span>
<h1 style='font-size: 40px; font-weight: 800; margin: 0; color: #FFFFFF; letter-spacing: -0.02em; line-height: 1;'>Pramaan</h1>
</div>
<p style='font-size: 14.5px; color: #94A3B8; margin-top: 6px; margin-bottom: 28px; line-height: 1.5; font-weight: 400;'>
Offline Cyber Forensic Triage & Multi-Entity Evidence Analytics Platform
</p>
<div style='display: flex; flex-direction: column; gap: 18px; margin-bottom: 24px;'>
<div style='display: flex; align-items: flex-start; gap: 14px;'>
<div style='background: rgba(255,255,255,0.1); min-width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px;'>🔒</div>
<div>
<div style='font-weight: 600; font-size: 13.5px; color: #F8FAFC;'>100% Local Hardware Execution</div>
<div style='font-size: 12px; color: #94A3B8;'>Zero network egress. Local SHA-256 evidence chain verification.</div>
</div>
</div>
<div style='display: flex; align-items: flex-start; gap: 14px;'>
<div style='background: rgba(255,255,255,0.1); min-width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px;'>🔍</div>
<div>
<div style='font-weight: 600; font-size: 13.5px; color: #F8FAFC;'>Multi-Source Artifact Parsing</div>
<div style='font-size: 12px; color: #94A3B8;'>Extract WhatsApp, Telegram, CDR, Bank Statements & EXIF data.</div>
</div>
</div>
<div style='display: flex; align-items: flex-start; gap: 14px;'>
<div style='background: rgba(255,255,255,0.1); min-width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px;'>🕸️</div>
<div>
<div style='font-weight: 600; font-size: 13.5px; color: #F8FAFC;'>Autonomous Risk Scoring Engine</div>
<div style='font-size: 12px; color: #94A3B8;'>Isolation Forest anomaly detection & interactive graph triage.</div>
</div>
</div>
</div>
</div>
<div style='border-top: 1px solid rgba(255,255,255,0.12); padding-top: 16px; display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; color: #64748B;'>
<span>Workstation #482-ZONE4</span>
<span>Build v1.0.0-offline</span>
</div>
</div>""",
            unsafe_allow_html=True
        )

    with col_form:
        with st.container(border=True):
            # Session expired banner
            if session_expired:
                render_banner(
                    kind="warning",
                    title="Session Expired",
                    body="Your session expired due to inactivity. Please sign in again."
                )

            st.markdown(
                """
                <div style='margin-bottom: 20px;'>
                    <div style='font-size: 22px; font-weight: 700; color: #0F172A; letter-spacing: -0.01em;'>Workstation Sign In</div>
                    <div style='font-size: 13px; color: #64748B; margin-top: 2px;'>Enter authorized badge credentials to unlock workstation</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Quick Demo Account Selector Box
            st.markdown(
                """
                <div style='background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 12px 14px; margin-bottom: 18px;'>
                    <div style='font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;'>
                        🔑 Quick Demo Auto-Fill
                    </div>
                    <div style='font-size: 12px; color: #64748B;'>
                        Click to pre-fill test officer credentials:
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            demo1, demo2 = st.columns(2)
            with demo1:
                if st.button("👮 Inspector Vikram\n(Supervisor)", key="demo_sup_btn", use_container_width=True):
                    st.session_state["s01_badge"] = "BP-94821"
                    st.session_state["s01_pwd"] = "Pramaan2026!"
                    st.rerun()
            
            with demo2:
                if st.button("🔍 SI Ananya Roy\n(IO)", key="demo_io_btn", use_container_width=True):
                    st.session_state["s01_badge"] = "BP-88104"
                    st.session_state["s01_pwd"] = "Officer@1234"
                    st.rerun()

            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

            # Form Inputs
            badge_no = st.text_input("Badge Number", placeholder="e.g. BP-94821", key="s01_badge")
            password = st.text_input("Password", type="password", placeholder="••••••••••••", key="s01_pwd")

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

            submit_clicked = btn_primary("🔒 Sign In to Workstation", key="s01_submit_btn", disabled=is_locked, use_container_width=True)

            if submit_clicked and not is_locked:
                if not badge_no.strip() or not password:
                    st.markdown("<div style='color: var(--risk-crit-fill); font-size: 13.5px; margin-top: 8px; font-weight: 500;'>⚠️ Badge number or password is incorrect.</div>", unsafe_allow_html=True)
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
                            st.markdown("<div style='color: var(--risk-crit-fill); font-size: 13.5px; margin-top: 8px; font-weight: 500;'>⚠️ Badge number or password is incorrect.</div>", unsafe_allow_html=True)

            st.markdown(
                """
                <div style='margin-top: 20px; padding-top: 14px; border-top: 1px solid #E2E8F0; text-align: center; font-size: 11px; color: #94A3B8;'>
                    <span class='tp-offline-pill'>Offline · No data leaves this workstation</span>
                </div>
                """,
                unsafe_allow_html=True
            )


