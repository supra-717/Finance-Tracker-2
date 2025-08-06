from datetime import datetime
import streamlit as st


def log_error(message: str) -> None:
    """Append a timestamped ``message`` to a session-scoped error log."""

    st.session_state.setdefault("error_log", []).append(
        f"{datetime.now():%H:%M:%S} - {message}"
    )
