import streamlit as st

from config import COL_TICKER, COL_SHARES, COL_PRICE
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
            st.session_state.pop("b_ticker", None)
            st.session_state.pop("b_shares", None)
            st.session_state.pop("b_price", None)
            st.session_state.pop("b_stop_pct", None)
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Buy"):
        with st.form("buy_form", clear_on_submit=True):
            st.text_input("Ticker", key="b_ticker", placeholder="e.g. AAPL")
            st.number_input(
                "Shares",
                min_value=1,
                value=1,
                step=1,
                key="b_shares",
            )
            st.number_input(
                "Price",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                key="b_price",
            )
            st.number_input(
                "Stop-loss %",
                min_value=0.0,
                value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                key="b_stop_pct",
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
            st.session_state.pop("s_ticker", None)
            st.session_state.pop("s_shares", None)
            st.session_state.pop("s_price", None)
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Sell", expanded=True):
        holdings = st.session_state.portfolio
        if holdings.empty:
            st.info("You have no holdings to sell.")
            return

        st.selectbox(
            "Ticker",
            options=holdings[COL_TICKER].tolist(),
            key="s_ticker",
        )
        matching = holdings[holdings[COL_TICKER] == st.session_state.s_ticker]
        if not matching.empty:
            max_shares = int(matching.iloc[0][COL_SHARES])
            latest_price = float(matching.iloc[0][COL_PRICE])
        else:
            max_shares = 0
            latest_price = 0.0

        if max_shares > 0:
            share_min = 1
            share_default = 1
        else:
            share_min = 0
            share_default = 0

        if max_shares == 0:
            st.info("You have no shares to sell for this ticker.")
        else:
            with st.form("sell_form", clear_on_submit=True):
                st.number_input(
                    "Shares to sell",
                    min_value=share_min,
                    value=share_default,
                    max_value=max_shares,
                    step=1,
                    key="s_shares",
                )
                st.number_input(
                    "Price",
                    min_value=0.0,
                    value=latest_price,
                    step=0.01,
                    format="%.2f",
                    key="s_price",
                )
                st.form_submit_button("Submit Sell", on_click=submit_sell)

