"""
Trace-Proof S03 — New Case Form (views/s03_case_new.py)
Full-screen layout (no sidebar).
Auto-suggested case number, validation, duplicate check, and folder creation error handling.
"""

import streamlit as st
import datetime
from views import api
from views.components.buttons import btn_primary, btn_secondary

def render_s03_case_new():
    """Renders S03 New Case screen."""

    st.markdown(
        """
        <div style='max-width: 680px; margin: 30px auto 16px auto;'>
            <div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 20px;'>
                <div>
                    <h1 class='tp-h1' style='margin: 0;'>New Case</h1>
                    <div class='tp-caption' style='margin-top: 2px;'>Initialize a new evidence folder and SQLite database for forensic triage.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.container():
        st.markdown("<div style='max-width: 680px; margin: 0 auto;' class='tp-card'>", unsafe_allow_html=True)

        officer = st.session_state.get("officer")
        created_by_badge = officer.badge_no if officer else "BP-94821"
        created_by_name = officer.full_name if officer else "Inspector Vikram Singh"

        # Auto-suggested case number
        auto_case_num = "CASE_2026_0143"
        
        col1, col2 = st.columns(2)
        with col1:
            case_number = st.text_input("Case Number *", value=auto_case_num, key="s03_num", help="Unique workstation case identifier.")
        with col2:
            fir_number = st.text_input("FIR Number (optional)", placeholder="e.g. FIR-2026-09124", key="s03_fir")

        title = st.text_input("Case Title / Subject *", placeholder="e.g. Investment Fraud — Cyber Cell Complaint #9412", key="s03_title")

        col3, col4 = st.columns(2)
        with col3:
            police_station = st.text_input("Police Station", value="Cyber Crime PS, Zone 4", key="s03_ps")
        with col4:
            complaint_date = st.date_input("Complaint Date", value=datetime.date.today(), key="s03_date")

        description = st.text_area("Short Description", placeholder="Brief summary of reported fraud, victim loss details, and suspected channels...", key="s03_desc", height=100)

        # Simulation checkbox for folder creation error test
        simulate_folder_err = st.checkbox("Simulate folder creation permission error", value=False, key="s03_sim_folder_err")

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        col_b1, col_b2, col_space = st.columns([0.3, 0.3, 0.4])
        with col_b1:
            submit_clicked = btn_primary("Create Case", key="s03_submit_btn", use_container_width=True)
        with col_b2:
            cancel_clicked = btn_secondary("Cancel", key="s03_cancel_btn", use_container_width=True)

        if cancel_clicked:
            st.query_params["view"] = "cases"
            st.rerun()

        if submit_clicked:
            errors = []
            if not case_number.strip():
                errors.append("Case number is required.")
            if not title.strip():
                errors.append("Case title is required.")

            # Duplicate check
            existing = api.get_case_by_id(case_number.strip())
            if existing:
                errors.append(f"A case with number '{case_number.strip()}' already exists on this workstation.")

            if simulate_folder_err:
                errors.append("Could not create the case folder. Check disk space and permissions.")

            if errors:
                for err in errors:
                    st.markdown(f"<div style='color: var(--risk-crit-fill); font-size: 13.5px; margin-top: 6px;'>• {err}</div>", unsafe_allow_html=True)
            else:
                new_c = api.create_case(
                    case_number=case_number.strip(),
                    title=title.strip(),
                    fir_number=fir_number.strip() if fir_number else None,
                    police_station=police_station.strip(),
                    complaint_date=complaint_date.strftime("%d %b %Y"),
                    description=description.strip(),
                    created_by_badge=created_by_badge,
                    created_by_name=created_by_name
                )
                st.session_state["current_case_id"] = new_c.id
                st.toast(f"Case {new_c.case_number} created successfully.")
                st.query_params["case"] = new_c.id
                st.query_params["view"] = "dashboard"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
