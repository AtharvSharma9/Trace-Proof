"""
Trace-Proof Screen Title Block Component (views/components/headers.py)
"""

import streamlit as st
from views.components.buttons import btn_primary

def render_screen_title(
    title: str,
    subtitle: str = "",
    breadcrumbs: str = "",
    primary_action_label: str = None,
    primary_action_key: str = None
) -> bool:
    """
    Renders standard screen header title block with primary action on the right.
    Returns True if primary action button was clicked.
    """
    col_title, col_action = st.columns([0.75, 0.25] if primary_action_label else [1.0, 0.0001])
    
    with col_title:
        if breadcrumbs:
            st.markdown(
                f"""<div style='font-size: 12px; color: var(--ink-muted); margin-bottom: 2px; font-weight: 500;'>{breadcrumbs}</div>""",
                unsafe_allow_html=True
            )
        st.markdown(
            f"""
            <div style='margin-bottom: 16px;'>
                <div class='tp-display'>{title}</div>
                {f"<div class='tp-body-sm' style='color: var(--ink-muted); margin-top: 2px;'>{subtitle}</div>" if subtitle else ""}
            </div>
            """,
            unsafe_allow_html=True
        )

    clicked = False
    if primary_action_label and primary_action_key:
        with col_action:
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            clicked = btn_primary(primary_action_label, key=primary_action_key, use_container_width=True)
            
def render_screen_header(title: str, subtitle: str = "") -> str:
    """
    Renders simple HTML string for screen title block.
    """
    return f"""
    <div style='border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 20px;'>
        <div class='tp-display'>{title}</div>
        {f"<div class='tp-body-sm' style='color: var(--ink-muted); margin-top: 2px;'>{subtitle}</div>" if subtitle else ""}
    </div>
    """

