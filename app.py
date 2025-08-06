"""Streamlit app for local portfolio tracking and AI‑assisted trading."""

import streamlit as st
from streamlit import config as _config

from ui.dashboard import render_dashboard
from ui.user_guide import render_user_guide

st.set_page_config(
    page_title="AI Assisted Trading",
    theme=_config.get_option("theme.base"),
)


def main() -> None:
    """Application entry point."""

    dashboard_tab, guide_tab = st.tabs(["Dashboard", "User Guide"])
    with dashboard_tab:
        render_dashboard()
    with guide_tab:
        render_user_guide()


if __name__ == "__main__":
    main()
