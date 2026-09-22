"""
Trace-Proof Button Components (views/components/buttons.py)
Supports Primary, Secondary, Ghost, Danger and Disabled buttons.
"""

import streamlit as st

def btn_primary(label: str, key: str = None, disabled: bool = False, help_text: str = None, use_container_width: bool = False) -> bool:
    """Renders the single Primary action button for a screen (Height 44px, --primary fill)."""
    return st.button(
        label,
        key=key,
        type="primary",
        disabled=disabled,
        help=help_text,
        use_container_width=use_container_width
    )

def btn_secondary(label: str, key: str = None, disabled: bool = False, help_text: str = None, use_container_width: bool = False) -> bool:
    """Renders a Secondary button (White fill, 1px border)."""
    return st.button(
        label,
        key=key,
        type="secondary",
        disabled=disabled,
        help=help_text,
        use_container_width=use_container_width
    )

def render_ghost_button(label: str, key: str = None, disabled: bool = False) -> bool:
    """Renders a Ghost action button (No fill, no border)."""
    return st.button(
        label,
        key=key,
        disabled=disabled,
        use_container_width=False
    )

def render_danger_button(label: str, key: str = None, disabled: bool = False, help_text: str = None) -> bool:
    """Renders a Danger action button (Red outline, requires confirmation/typed reason)."""
    return st.button(
        label,
        key=key,
        disabled=disabled,
        help=help_text
    )
