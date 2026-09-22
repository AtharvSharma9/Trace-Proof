"""
Trace-Proof Status Banner Component (views/components/banners.py)
Renders full-width status banners: Success, Warning, Error, Info.
"""

import streamlit as st
from views.components.icons import icon_svg

def render_banner(
    kind: str,
    title: str,
    body: str = "",
    action_label: str = None,
    action_key: str = None
) -> bool:
    """
    Renders a status banner.
    kind: 'success' | 'warning' | 'error' | 'info'
    Returns True if the action button was clicked.
    """
    icon_map = {
        "success": icon_svg("check-circle", size=20, color="#15803D"),
        "warning": icon_svg("alert-triangle", size=20, color="#B45309"),
        "error": icon_svg("x-circle", size=20, color="#B91C1C"),
        "info": icon_svg("info", size=20, color="#1B3A5C")
    }

    ic = icon_map.get(kind, icon_map["info"])
    
    col_content, col_action = st.columns([0.85, 0.15] if action_label else [1.0, 0.0001])
    
    with col_content:
        st.markdown(
            f"""
            <div class='tp-banner {kind}'>
                <div style='display: flex; gap: 12px; align-items: flex-start;'>
                    <div style='margin-top: 1px;'>{ic}</div>
                    <div>
                        <div class='title'>{title}</div>
                        {f"<div class='body'>{body}</div>" if body else ""}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    clicked = False
    if action_label and action_key:
        with col_action:
            clicked = st.button(action_label, key=action_key)
            
    return clicked

def render_status_banner(kind: str, message: str) -> str:
    """
    Returns HTML banner for success/warning/error/info messages.
    """
    return f"""
    <div class='tp-banner {kind}'>
        <div style='display: flex; gap: 12px; align-items: flex-start;'>
            <div>
                <div class='title'>{kind.upper()}</div>
                <div class='body'>{message}</div>
            </div>
        </div>
    </div>
    """

