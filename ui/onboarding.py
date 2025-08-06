import streamlit as st


def show_onboarding() -> None:
    """Display a simple onboarding message for first-time users."""

    if st.session_state.get("show_info", True):
        st.info(
            "Use the controls below to manage your portfolio. Data is stored in the local `data/` directory."
        )
        st.button(
            "Dismiss",
            on_click=lambda: st.session_state.update(show_info=False),
            key="dismiss_onboard",
        )
