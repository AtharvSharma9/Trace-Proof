"""
Pramaan Screen S12: Chronological Timeline (views/s12_timeline.py)
Unified timeline of transactions, call logs, IP sessions, and SIM events.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_header
from views.components.captions import render_provenance_caption, render_table_header_caption


def render_s12_timeline():
    case_id = st.session_state.get("current_case_id", "case_2026_0142")
    
    st.markdown(
        render_screen_header(
            title="Chronological Event Timeline",
            subtitle="Unified temporal sequence of transactions, call logs, IP sessions, and SIM switches."
        ),
        unsafe_allow_html=True
    )
    
    events = api.list_timeline_events(case_id)
    
    # Filter controls
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1:
        search_query = st.text_input("Search Timeline", placeholder="Filter by account, number, location, or amount...", key="s12_search")
    with col2:
        event_type_filter = st.selectbox("Event Type", ["ALL", "BANK_TRANSFER", "CALL", "ATM_WITHDRAWAL", "IP_LOG"], key="s12_type")
    with col3:
        entity_filter = st.selectbox(
            "Filter by Entity", 
            ["ALL", "SBI 10928374651", "HDFC 9876543210", "Airtel +91-9876543210", "ATM-DELHI-SOUTH-04"],
            key="s12_entity"
        )
        
    # Apply filters
    filtered_events = events
    if event_type_filter != "ALL":
        filtered_events = [ev for ev in filtered_events if ev.event_type == event_type_filter]
    if search_query:
        q = search_query.lower()
        filtered_events = [
            ev for ev in filtered_events 
            if q in ev.event_time.lower() or q in ev.description.lower() or q in str(ev.amount)
        ]
        
    st.markdown(render_table_header_caption("Chronological Events", len(filtered_events), "Sorted by datetime asc"), unsafe_allow_html=True)
    
    for idx, ev in enumerate(filtered_events):
        with st.container():
            t_col, icon_col, detail_col = st.columns([2.5, 1, 6.5])
            
            with t_col:
                st.markdown(f"<div style='font-family: \"JetBrains Mono\", monospace; font-size: 13px; font-weight: 600; color: var(--navy);'>{ev.event_time}</div>", unsafe_allow_html=True)
                st.caption(f"Sequence #{idx+1}")
                
            with icon_col:
                badge_bg = "#f1f5f9"
                badge_fg = "#334155"
                if "TRANSFER" in ev.event_type or "UPI" in ev.event_type:
                    badge_bg = "#eff6ff"
                    badge_fg = "#1e40af"
                elif "ATM" in ev.event_type or "WITHDRAWAL" in ev.event_type:
                    badge_bg = "#fef2f2"
                    badge_fg = "#991b1b"
                elif "CALL" in ev.event_type:
                    badge_bg = "#f0fdf4"
                    badge_fg = "#166534"
                    
                st.markdown(f"<span style='background: {badge_bg}; color: {badge_fg}; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;'>{ev.event_type}</span>", unsafe_allow_html=True)
                
            with detail_col:
                # Event summary line
                amount_str = f" · <strong style='color: var(--risk-crit-fill);'>₹{ev.amount:,.2f}</strong>" if ev.amount else ""
                
                st.markdown(
                    f"<span style='font-size: 13.5px; font-weight: 500;'>{ev.description}</span>{amount_str}",
                    unsafe_allow_html=True
                )
                
                # Provenance expander
                with st.expander("Raw Evidence Provenance", expanded=False):
                    st.markdown(
                        render_provenance_caption(ev.source_filename, ev.source_row, ev.source_sha256),
                        unsafe_allow_html=True
                    )
                    st.markdown(f"""
                    <div style='background: var(--surface-alt); padding: 8px 12px; border-radius: 4px; border: 1px solid var(--border); margin-top: 6px; font-family: "JetBrains Mono", monospace; font-size: 12px;'>
                        Source File: {ev.source_filename}<br/>
                        Row Number: {ev.source_row}<br/>
                        File SHA-256: {ev.source_sha256}
                    </div>
                    """, unsafe_allow_html=True)
                    
            st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
