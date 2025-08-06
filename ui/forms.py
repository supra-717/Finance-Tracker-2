import streamlit as st

from config import COL_TICKER
from services.market import fetch_price
from services.trading import manual_buy, manual_sell


def show_buy_form() -> None:
    """Render and process the buy form inside an expander."""

    def submit_buy() -> None:
        if st.session_state.b_shares <= 0 or st.session_state.b_price <= 0:
            st.session_state.feedback = (
                "error",
                "Shares and price must be positive.",
            )
            return
        ok, msg, port, cash = manual_buy(
            st.session_state.b_ticker,
            st.session_state.b_shares,
            st.session_state.b_price,
            st.session_state.b_price * (1 - st.session_state.b_stop_pct / 100)
            if st.session_state.b_price > 0 and st.session_state.b_stop_pct > 0
            else 0.0,
            st.session_state.portfolio,
            st.session_state.cash,
        )
        if ok:
            st.session_state.portfolio = port
            st.session_state.cash = cash
            st.session_state.feedback = ("success", msg)
            st.session_state.b_ticker = ""
            st.session_state.b_shares = 0.0
            st.session_state.b_price = 0.0
            st.session_state.b_stop_pct = 0.0
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Buy"):
        with st.form("buy_form", clear_on_submit=True):
            ticker = st.text_input("Ticker", key="b_ticker")
            st.number_input("Shares", min_value=1, step=1, key="b_shares")
            latest = fetch_price(ticker) if ticker else 0.0
            st.number_input(
                "Price", min_value=1.0, step=0.01, format="%.2f", key="b_price", value=latest or 1.0
            )
            st.number_input(
                "Stop Loss %", min_value=0.0, format="%.1f", key="b_stop_pct"
            )
            if st.session_state.b_price > 0 and st.session_state.b_stop_pct > 0:
                calc_stop = st.session_state.b_price * (
                    1 - st.session_state.b_stop_pct / 100
                )
                st.caption(f"Stop loss price: ${calc_stop:.2f}")
            st.form_submit_button("Submit Buy", on_click=submit_buy)

def show_sell_form() -> None:
    """Render and process the sell form inside an expander."""

    def submit_sell() -> None:
        if st.session_state.s_shares <= 0 or st.session_state.s_price <= 0:
            st.session_state.feedback = (
                "error",
                "Shares and price must be positive.",
            )
            return
        ok, msg, port, cash = manual_sell(
            st.session_state.s_ticker,
            st.session_state.s_shares,
            st.session_state.s_price,
            st.session_state.portfolio,
            st.session_state.cash,
        )
        if ok:
            st.session_state.portfolio = port
            st.session_state.cash = cash
            st.session_state.feedback = ("success", msg)
            st.session_state.s_ticker = ""
            st.session_state.s_shares = 0.0
            st.session_state.s_price = 0.0
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Sell"):
        with st.form("sell_form", clear_on_submit=True):
            tickers = st.session_state.portfolio[COL_TICKER].tolist()
            st.selectbox("Ticker", tickers, key="s_ticker")
            st.number_input("Shares", min_value=1, step=1, key="s_shares")
            st.number_input("Price", min_value=1.0, step=0.01, format="%.2f", key="s_price")
            st.form_submit_button("Submit Sell", on_click=submit_sell)

