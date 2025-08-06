import pandas as pd
import streamlit as st
import yfinance as yf

from config import COL_TICKER
from data.watchlist import save_watchlist
from services.market import fetch_price, fetch_prices


def show_watchlist_sidebar() -> None:
    """Render ticker lookup and watchlist in the sidebar."""

    sidebar = st.sidebar
    sidebar.header("Ticker Lookup")
    feedback_slot = sidebar.empty()

    def add_watchlist_and_clear(sym: str, price: float, portfolio_tickers: set[str]) -> None:
        """Callback to add ``sym`` to the watchlist and reset lookup fields."""

        if sym in st.session_state.watchlist:
            st.session_state.watchlist_feedback = ("info", f"{sym} already in watchlist.")
        elif sym in portfolio_tickers:
            st.session_state.watchlist_feedback = ("info", f"{sym} already in portfolio.")
        else:
            st.session_state.watchlist.append(sym)
            st.session_state.watchlist_prices[sym] = price
            save_watchlist(st.session_state.watchlist)
            st.session_state.watchlist_feedback = ("success", f"{sym} added to watchlist.")
        st.session_state.lookup_symbol = ""

    portfolio_tickers = (
        set(st.session_state.portfolio[COL_TICKER].values)
        if not st.session_state.portfolio.empty
        else set()
    )
    removed = [t for t in st.session_state.watchlist if t in portfolio_tickers]
    if removed:
        st.session_state.watchlist = [t for t in st.session_state.watchlist if t not in removed]
        for t in removed:
            st.session_state.watchlist_prices.pop(t, None)
        save_watchlist(st.session_state.watchlist)
        st.session_state.watchlist_feedback = (
            "info",
            f"Removed {', '.join(removed)} from watchlist (now in portfolio).",
        )

    error_slot = sidebar.empty()
    symbol = sidebar.text_input("Symbol", key="lookup_symbol", placeholder="e.g. AAPL")
    lookup_error = ""
    if symbol:
        sym = symbol.upper()
        price = fetch_price(sym)
        if price is None:
            lookup_error = "Ticker not found."
        else:
            ticker_obj = yf.Ticker(sym)
            name = ticker_obj.info.get("shortName") or ticker_obj.info.get("longName") or sym
            sidebar.write(f"{name}: ${price:.2f}")
            sidebar.button(
                "Add to Watchlist",
                key="add_watchlist",
                on_click=add_watchlist_and_clear,
                args=(sym, price, portfolio_tickers),
            )

    if lookup_error:
        error_slot.error(lookup_error)

    if st.session_state.watchlist:
        header = sidebar.container()
        hcol1, hcol2 = header.columns([4, 1])
        hcol1.subheader("Watchlist")
        if hcol2.button("\ud83d\udd04", key="refresh_watchlist", help="Refresh prices"):
            data = fetch_prices(st.session_state.watchlist)
            updated: dict[str, float | None] = {t: None for t in st.session_state.watchlist}
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    close = data["Close"].iloc[-1]
                    for t in st.session_state.watchlist:
                        val = close.get(t)
                        if val is not None and not pd.isna(val):
                            updated[t] = float(val)
                else:
                    val = data["Close"].iloc[-1]
                    if st.session_state.watchlist and not pd.isna(val):
                        updated[st.session_state.watchlist[0]] = float(val)
            st.session_state.watchlist_prices.update(updated)

        sidebar.markdown(
            "<style>.wl-remove{color:red; border:none; background:none; font-size:18px;}\n</style>",
            unsafe_allow_html=True,
        )
        for t in list(st.session_state.watchlist):
            price = st.session_state.watchlist_prices.get(t)
            price_str = f"${price:.2f}" if price is not None else "N/A"
            col1, col2 = sidebar.columns([4, 1])
            col1.write(f"{t}: {price_str}")
            if col2.button("\u274c", key=f"rm_{t}", help="Remove", use_container_width=True):
                st.session_state.watchlist.remove(t)
                st.session_state.watchlist_prices.pop(t, None)
                save_watchlist(st.session_state.watchlist)
                st.session_state.watchlist_feedback = (
                    "info",
                    f"Removed {t} from watchlist.",
                )

    if st.session_state.watchlist_feedback:
        kind, text = st.session_state.watchlist_feedback
        getattr(feedback_slot, kind)(text)
        st.session_state.watchlist_feedback = None
