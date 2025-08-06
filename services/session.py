import streamlit as st

from config import WATCHLIST_FILE
from data.portfolio import load_portfolio
from data.watchlist import load_watchlist


def init_session_state() -> None:
    """Initialise default values in ``st.session_state`` on first run."""

    for key, default in {
        "b_ticker": "",
        "b_shares": 1.0,
        "b_price": 1.0,
        "b_stop_pct": 0.0,
        "s_ticker": "",
        "s_shares": 1.0,
        "s_price": 1.0,
        "ac_amount": 0.0,
        "lookup_symbol": "",
        "watchlist_feedback": None,
        "watchlist": [],
        "watchlist_prices": {},
        "show_cash_form": False,
        "daily_summary": "",
        "show_info": True,
    }.items():
        st.session_state.setdefault(key, default)

    if "portfolio" not in st.session_state:
        port, cash, needs_cash = load_portfolio()
        st.session_state.portfolio = port
        st.session_state.cash = cash
        st.session_state.needs_cash = needs_cash

    if not st.session_state.watchlist and WATCHLIST_FILE.exists():
        st.session_state.watchlist = load_watchlist()
