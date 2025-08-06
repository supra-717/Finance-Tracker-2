import streamlit as st


def show_onboarding() -> None:
    """Display a simple onboarding message for first-time users."""

    if not st.session_state.get("dismissed_onboarding"):
        def dismiss() -> None:
            st.session_state.dismissed_onboarding = True
            st.rerun()

        st.info(
            "Use the controls below to manage your portfolio. Data is stored in the local `data/` directory."
        )
        st.button("Dismiss", key="dismiss_onboard", on_click=dismiss)


def dismiss_summary() -> None:
    """Hide the daily summary and immediately rerun the app."""

    st.session_state.daily_summary = ""
    st.rerun()
