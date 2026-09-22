"""
Trace-Proof Empty State Component (views/components/empty_state.py)
"""

import streamlit as st
from views.components.icons import icon_svg
from views.components.buttons import btn_primary

def render_empty_state(
    icon_name: str,
    title: str,
    subtext: str,
    action_label: str = None,
    action_key: str = None,
    secondary_action_label: str = None,
    secondary_action_key: str = None
) -> tuple[bool, bool]:
    """
    Renders standard empty state component.
    Returns (primary_clicked, secondary_clicked)
    """
    ic = icon_svg(icon_name, size=40, color="var(--ink-faint)")
    
    st.markdown(
        f"""
        <div class='tp-empty-state'>
            <div class='icon'>{ic}</div>
            <div class='title'>{title}</div>
            <div class='subtext'>{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    primary_clicked = False
    secondary_clicked = False
    
    if action_label or secondary_action_label:
        col_space1, col_btns, col_space2 = st.columns([0.3, 0.4, 0.3])
        with col_btns:
            if action_label and action_key:
                primary_clicked = btn_primary(action_label, key=action_key, use_container_width=True)
            if secondary_action_label and secondary_action_key:
                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                secondary_clicked = st.button(secondary_action_label, key=secondary_action_key, use_container_width=True)
                
    return primary_clicked, secondary_clicked
