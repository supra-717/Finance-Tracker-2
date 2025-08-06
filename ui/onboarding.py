import streamlit as st


def show_onboarding() -> None:
    """Display a simple onboarding message for first-time users."""

    if st.session_state.get("show_info", True):
        st.info(
            "Use the controls below to manage your portfolio. Data is stored in the local `data/` directory."
        )
        if st.button("Dismiss", key="dismiss_onboard"):
            st.session_state.show_info = False


def dismiss_summary() -> None:
    """Hide the daily summary."""

    st.session_state.daily_summary = ""
