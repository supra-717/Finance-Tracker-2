"""Streamlit app for managing the ChatGPT micro-cap portfolio.

The original implementation grew organically and contained a mix of UI and
backend logic, duplicated blocks, and sparse documentation.  This refactor
tidies the structure, centralises repeated behaviours, and adds explicit
docstrings and inline comments to make the application easier for developers
to understand and extend.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "Scripts and CSV Files"
PORTFOLIO_CSV = DATA_DIR / "chatgpt_portfolio_update.csv"
TRADE_LOG_CSV = DATA_DIR / "chatgpt_trade_log.csv"

# Today's date used for all new logs.
TODAY = datetime.today().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_portfolio() -> tuple[pd.DataFrame, float, bool]:
    """Return the latest portfolio and cash balance.

    The boolean flag indicates whether initialisation is required (e.g. the CSV
    is missing or lacks a cash balance) so the UI can prompt the user for a
    starting amount.
    """

    empty_portfolio = pd.DataFrame(
        columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]
    )

    if not PORTFOLIO_CSV.exists():
        return empty_portfolio, 0.0, True

    try:
        df = pd.read_csv(PORTFOLIO_CSV)
    except pd.errors.EmptyDataError:
        return empty_portfolio, 0.0, True

    if df.empty:
        return empty_portfolio, 0.0, True

    non_total = df[df["Ticker"] != "TOTAL"].copy()
    if non_total.empty:
        portfolio = empty_portfolio.copy()
    else:
        non_total["Date"] = pd.to_datetime(non_total["Date"])
        latest_date = non_total["Date"].max()
        latest = non_total[non_total["Date"] == latest_date].copy()
        latest.rename(
            columns={
                "Ticker": "ticker",
                "Shares": "shares",
                "Stop Loss": "stop_loss",
                "Cost Basis": "buy_price",
            },
            inplace=True,
        )
        latest["cost_basis"] = latest["shares"] * latest["buy_price"]
        portfolio = latest[
            ["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]
        ].reset_index(drop=True)

    total_rows = df[df["Ticker"] == "TOTAL"].copy()
    if total_rows.empty:
        cash = 0.0
        return portfolio, cash, True

    total_rows["Date"] = pd.to_datetime(total_rows["Date"])
    cash = float(total_rows.sort_values("Date").iloc[-1]["Cash Balance"])

    return portfolio, cash, False

def save_portfolio_snapshot(portfolio_df: pd.DataFrame, cash: float) -> pd.DataFrame:
    """Recalculate today's portfolio values and persist them to ``PORTFOLIO_CSV``."""

    results: list[dict[str, float | str]] = []
    total_value = 0.0
    total_pnl = 0.0

    for _, row in portfolio_df.iterrows():
        ticker = row["ticker"]
        shares = float(row["shares"])
        stop = float(row["stop_loss"])
        cost = float(row["buy_price"])

        data = yf.download(ticker, period="1d", progress=False)
        price = float(data["Close"].iloc[-1]) if not data.empty else 0.0
        value = round(price * shares, 2)
        pnl = round((price - cost) * shares, 2)
        total_value += value
        total_pnl += pnl

        results.append(
            {
                "Date": TODAY,
                "Ticker": ticker,
                "Shares": shares,
                "Cost Basis": cost,
                "Stop Loss": stop,
                "Current Price": price,
                "Total Value": value,
                "PnL": pnl,
                "Action": "HOLD",
                "Cash Balance": "",
                "Total Equity": "",
            }
        )

    total_row = {
        "Date": TODAY,
        "Ticker": "TOTAL",
        "Shares": "",
        "Cost Basis": "",
        "Stop Loss": "",
        "Current Price": "",
        "Total Value": round(total_value, 2),
        "PnL": round(total_pnl, 2),
        "Action": "",
        "Cash Balance": round(cash, 2),
        "Total Equity": round(total_value + cash, 2),
    }
    results.append(total_row)

    df = pd.DataFrame(results)
    if PORTFOLIO_CSV.exists():
        existing = pd.read_csv(PORTFOLIO_CSV)
        existing = existing[existing["Date"] != TODAY]
        df = pd.concat([existing, df], ignore_index=True)
    df.to_csv(PORTFOLIO_CSV, index=False)
    return df


def get_day_high_low(ticker: str) -> tuple[float, float]:
    """Return today's high and low price for ``ticker``.

    Raises ``RuntimeError`` if the ticker data cannot be downloaded and
    ``ValueError`` if no market data is returned.
    """

    try:
        data = yf.download(ticker, period="1d", progress=False)
    except Exception as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Data download failed: {exc}") from exc
    if data.empty:
        raise ValueError("No market data available.")
    return float(data["High"].iloc[-1]), float(data["Low"].iloc[-1])


def append_trade_log(log: dict) -> None:
    """Append a dictionary entry to the trade log CSV."""

    if TRADE_LOG_CSV.exists():
        existing = pd.read_csv(TRADE_LOG_CSV)
        log_df = pd.concat([existing, pd.DataFrame([log])], ignore_index=True)
    else:
        log_df = pd.DataFrame([log])
    log_df.to_csv(TRADE_LOG_CSV, index=False)

def manual_buy(
    ticker: str,
    shares: float,
    price: float,
    stop_loss: float,
    portfolio_df: pd.DataFrame,
    cash: float,
) -> tuple[bool, str, pd.DataFrame, float]:
    """Execute a manual buy and update portfolio and logs."""

    ticker = ticker.upper()
    try:
        day_high, day_low = get_day_high_low(ticker)
    except Exception as exc:  # pragma: no cover - network errors
        return False, str(exc), portfolio_df, cash

    if not (day_low <= price <= day_high):
        msg = f"Price outside today's range {day_low:.2f}-{day_high:.2f}"
        return False, msg, portfolio_df, cash

    cost = price * shares
    if cost > cash:
        return False, "Insufficient cash for this trade.", portfolio_df, cash

    log = {
        "Date": TODAY,
        "Ticker": ticker,
        "Shares Bought": shares,
        "Buy Price": price,
        "Cost Basis": cost,
        "PnL": 0.0,
        "Reason": "MANUAL BUY - New position",
    }
    append_trade_log(log)

    mask = portfolio_df["ticker"] == ticker
    if not mask.any():
        new_row = {
            "ticker": ticker,
            "shares": shares,
            "stop_loss": stop_loss,
            "buy_price": price,
            "cost_basis": cost,
        }
        portfolio_df = pd.concat(
            [portfolio_df, pd.DataFrame([new_row])], ignore_index=True
        )
    else:
        idx = portfolio_df[mask].index[0]
        current_shares = float(portfolio_df.at[idx, "shares"])
        current_cost = float(portfolio_df.at[idx, "cost_basis"])
        portfolio_df.at[idx, "shares"] = current_shares + shares
        portfolio_df.at[idx, "cost_basis"] = current_cost + cost
        portfolio_df.at[idx, "buy_price"] = (
            portfolio_df.at[idx, "cost_basis"] / portfolio_df.at[idx, "shares"]
        )
        portfolio_df.at[idx, "stop_loss"] = stop_loss

    cash -= cost
    save_portfolio_snapshot(portfolio_df, cash)
    msg = f"Bought {shares} shares of {ticker} at ${price:.2f}."
    return True, msg, portfolio_df, cash

def manual_sell(
    ticker: str,
    shares: float,
    price: float,
    portfolio_df: pd.DataFrame,
    cash: float,
) -> tuple[bool, str, pd.DataFrame, float]:
    """Execute a manual sell and update portfolio and logs."""

    ticker = ticker.upper()
    if ticker not in portfolio_df["ticker"].values:
        return False, "Ticker not in portfolio.", portfolio_df, cash

    try:
        day_high, day_low = get_day_high_low(ticker)
    except Exception as exc:  # pragma: no cover - network errors
        return False, str(exc), portfolio_df, cash

    if not (day_low <= price <= day_high):
        msg = f"Price outside today's range {day_low:.2f}-{day_high:.2f}"
        return False, msg, portfolio_df, cash

    row = portfolio_df[portfolio_df["ticker"] == ticker].iloc[0]
    total_shares = float(row["shares"])
    if shares > total_shares:
        msg = f"Trying to sell {shares} shares but only own {total_shares}."
        return False, msg, portfolio_df, cash

    buy_price = float(row["buy_price"])
    cost_basis = buy_price * shares
    pnl = price * shares - cost_basis

    log = {
        "Date": TODAY,
        "Ticker": ticker,
        "Shares Bought": "",
        "Buy Price": "",
        "Cost Basis": cost_basis,
        "PnL": pnl,
        "Reason": "MANUAL SELL - User",
        "Shares Sold": shares,
        "Sell Price": price,
    }
    append_trade_log(log)

    if shares == total_shares:
        portfolio_df = portfolio_df[portfolio_df["ticker"] != ticker]
    else:
        idx = portfolio_df[portfolio_df["ticker"] == ticker].index[0]
        portfolio_df.at[idx, "shares"] = total_shares - shares
        portfolio_df.at[idx, "cost_basis"] = portfolio_df.at[idx, "shares"] * buy_price

    cash += price * shares
    save_portfolio_snapshot(portfolio_df, cash)
    msg = f"Sold {shares} shares of {ticker} at ${price:.2f}."
    return True, msg, portfolio_df, cash

def init_session_state() -> None:
    """Initialise default values in ``st.session_state`` on first run."""

    for key, default in {
        "b_ticker": "",
        "b_shares": 0.0,
        "b_price": 0.0,
        "b_stop": 0.0,
        "s_ticker": "",
        "s_shares": 0.0,
        "s_price": 0.0,
        "ac_amount": 0.0,
        "watchlist": [],
        # Cache of latest watchlist prices fetched via the refresh button.
        "watchlist_prices": {},
        # Toggle for showing the inline "Add Cash" form.
        "show_cash_form": False,
    }.items():
        st.session_state.setdefault(key, default)

    if "portfolio" not in st.session_state:
        port, cash, needs_cash = load_portfolio()
        st.session_state.portfolio = port
        st.session_state.cash = cash
        st.session_state.needs_cash = needs_cash


def show_watchlist_sidebar() -> None:
    """Render ticker lookup and watchlist in the sidebar."""

    sidebar = st.sidebar
    sidebar.header("Ticker Lookup")

    # Remove any watched tickers that are now held in the portfolio.
    portfolio_tickers = (
        set(st.session_state.portfolio["ticker"].values)
        if not st.session_state.portfolio.empty
        else set()
    )
    removed = [t for t in st.session_state.watchlist if t in portfolio_tickers]
    if removed:
        st.session_state.watchlist = [t for t in st.session_state.watchlist if t not in removed]
        # Drop any cached prices for tickers that moved into the portfolio.
        for t in removed:
            st.session_state.watchlist_prices.pop(t, None)
        st.session_state.feedback = (
            "info",
            f"Removed {', '.join(removed)} from watchlist (now in portfolio).",
        )

    # Lookup form for a single ticker symbol.
    symbol = sidebar.text_input("Symbol", key="lookup_symbol", placeholder="e.g. AAPL")
    if symbol:
        sym = symbol.upper()
        try:
            ticker_obj = yf.Ticker(sym)
            hist = ticker_obj.history(period="1d")
            if hist.empty:
                raise ValueError
            price = float(hist["Close"].iloc[-1])
            name = ticker_obj.info.get("shortName") or ticker_obj.info.get("longName") or sym
            sidebar.write(f"{name}: ${price:.2f}")
            if sidebar.button("Add to Watchlist", key="add_watchlist"):
                if sym in st.session_state.watchlist:
                    st.session_state.feedback = ("info", f"{sym} already in watchlist.")
                elif sym in portfolio_tickers:
                    st.session_state.feedback = ("info", f"{sym} already in portfolio.")
                else:
                    st.session_state.watchlist.append(sym)
                    st.session_state.watchlist_prices[sym] = price
                    st.session_state.feedback = ("success", f"{sym} added to watchlist.")
        except Exception:
            sidebar.error("Ticker not found.")

    if st.session_state.watchlist:
        sidebar.subheader("Watchlist")

        # Manual refresh to update all stored prices.
        if sidebar.button("Refresh Prices", key="refresh_watchlist"):
            updated: dict[str, float | None] = {}
            for t in st.session_state.watchlist:
                try:
                    data = yf.download(t, period="1d", progress=False)
                    price = float(data["Close"].iloc[-1]) if not data.empty else None
                except Exception:
                    price = None
                updated[t] = price
            st.session_state.watchlist_prices.update(updated)

        # Styling so the remove button only appears on hover. Streamlit has no
        # native hover callbacks, so a small CSS snippet is used as a
        # lightweight workaround.
        sidebar.markdown(
            """
            <style>
            .watchlist-item {display:flex; justify-content:space-between; align-items:center;}
            .watchlist-item button {
                visibility:hidden;
                color:white;
                background-color:red;
                border:none;
                border-radius:50%;
                width:1.2em; height:1.2em;
                padding:0; line-height:1.2em;
            }
            .watchlist-item:hover button {visibility:visible;}
            </style>
            """,
            unsafe_allow_html=True,
        )

        for t in st.session_state.watchlist.copy():
            price = st.session_state.watchlist_prices.get(t)
            display_price = f"${price:.2f}" if price is not None else "N/A"
            item = sidebar.container()
            item.markdown("<div class='watchlist-item'>", unsafe_allow_html=True)
            col1, col2 = item.columns([4,1])
            col1.write(f"{t}: {display_price}")
            if col2.button("✖", key=f"rm_{t}"):
                st.session_state.watchlist.remove(t)
                st.session_state.watchlist_prices.pop(t, None)
                st.session_state.feedback = ("info", f"{t} removed from watchlist.")
                st.rerun()
            item.markdown("</div>", unsafe_allow_html=True)


def show_buy_form() -> None:
    """Render and process the buy form inside an expander."""

    def submit_buy() -> None:
        """Handle Buy submission and reset the form via callback."""

        ok, msg, port, cash = manual_buy(
            st.session_state.b_ticker,
            st.session_state.b_shares,
            st.session_state.b_price,
            st.session_state.b_stop,
            st.session_state.portfolio,
            st.session_state.cash,
        )
        if ok:
            st.session_state.portfolio = port
            st.session_state.cash = cash
            ticker = st.session_state.b_ticker.upper()
            # Remove from watchlist if the ticker was previously being watched.
            if ticker in st.session_state.watchlist:
                st.session_state.watchlist.remove(ticker)
                st.session_state.watchlist_prices.pop(ticker, None)
                msg += f" {ticker} removed from watchlist."
            st.session_state.feedback = ("success", msg)
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Buy"):
        with st.form("buy_form", clear_on_submit=True):
            st.text_input("Ticker", key="b_ticker")
            st.number_input("Shares", min_value=0.0, step=1.0, key="b_shares")
            st.number_input("Price", min_value=0.0, format="%.2f", key="b_price")
            st.number_input("Stop-loss", min_value=0.0, format="%.2f", key="b_stop")
            # Use ``on_click`` callback so state mutations occur in the
            # callback rather than in-line after widget definition.
            st.form_submit_button("Submit Buy", on_click=submit_buy)


def show_sell_form() -> None:
    """Render and process the sell form inside an expander."""

    def submit_sell() -> None:
        """Handle Sell submission and reset the form via callback."""

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
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Sell"):
        with st.form("sell_form", clear_on_submit=True):
            st.text_input("Ticker", key="s_ticker")
            st.number_input("Shares", min_value=0.0, step=1.0, key="s_shares")
            st.number_input("Price", min_value=0.0, format="%.2f", key="s_price")
            # Trigger callback to perform sell and clear state safely.
            st.form_submit_button("Submit Sell", on_click=submit_sell)


def show_cash_section() -> None:
    """Display cash balance with an inline form to add funds."""

    def submit_cash() -> None:
        """Update cash balance, persist change, then hide the form."""

        amount = st.session_state.ac_amount
        if amount <= 0:
            st.session_state.feedback = (
                "error",
                "Amount must be greater than zero.",
            )
            return

        st.session_state.cash += amount
        save_portfolio_snapshot(st.session_state.portfolio, st.session_state.cash)
        st.session_state.feedback = (
            "success",
            f"Added ${amount:.2f} to cash balance.",
        )
        # Hide the form again after successful submission.
        st.session_state.show_cash_form = False

    st.subheader("Cash Balance")
    col1, col2 = st.columns([3, 1])

    # Display the cash amount without a redundant label.
    with col1:
        st.markdown(f"<h3>${st.session_state.cash:.2f}</h3>", unsafe_allow_html=True)

    with col2:
        if st.session_state.show_cash_form:
            # Inline form shown when the button is clicked.
            with st.form("add_cash_form", clear_on_submit=True):
                st.number_input(
                    "Amount",
                    min_value=0.0,
                    format="%.2f",
                    key="ac_amount",
                )
                st.form_submit_button("Add Cash", on_click=submit_cash)
        else:
            st.button(
                "Add Cash",
                on_click=lambda: st.session_state.update(show_cash_form=True),
            )


def main() -> None:
    """Entry point for the Streamlit UI."""

    st.title("ChatGPT Portfolio Manager")
    init_session_state()
    show_watchlist_sidebar()

    # Display feedback messages once and remove from session state so they
    # do not linger between reruns.
    feedback = st.session_state.pop("feedback", None)
    if feedback:
        kind, text = feedback
        if kind == "success":
            st.success(text)
        elif kind == "error":
            st.error(text)
        else:
            st.info(text)

    if st.session_state.get("needs_cash", False):
        # Prompt for starting cash on first-time use.
        st.subheader("Initialize Portfolio")
        with st.form("init_cash_form", clear_on_submit=True):
            start_cash_raw = st.text_input(
                "Enter starting cash",
                key="start_cash",
                placeholder="0.00",
            )
            init_submit = st.form_submit_button("Set Starting Cash")
        if init_submit:
            try:
                start_cash = float(start_cash_raw)
                if start_cash <= 0:
                    raise ValueError
            except ValueError:
                st.session_state.feedback = (
                    "error",
                    "Please enter a positive number.",
                )
            else:
                st.session_state.cash = start_cash
                st.session_state.needs_cash = False
                save_portfolio_snapshot(
                    st.session_state.portfolio, st.session_state.cash
                )
                st.session_state.feedback = (
                    "success",
                    f"Starting cash of ${start_cash:.2f} recorded.",
                )
            st.rerun()
        return

    # Always refresh today's snapshot and totals once cash is initialised
    summary_df = save_portfolio_snapshot(
        st.session_state.portfolio, st.session_state.cash
    )

    # ------------------------------------------------------------------
    # Section 1: Cash Balance & Add Cash
    # ------------------------------------------------------------------
    show_cash_section()

    # ------------------------------------------------------------------
    # Section 2: Current Portfolio Table
    # ------------------------------------------------------------------
    st.subheader("Current Portfolio")
    port_table = summary_df[summary_df["Ticker"] != "TOTAL"].copy()
    if port_table.empty:
        st.info("Your portfolio is empty. Log a trade below.")
    else:
        # Ensure numeric types for calculations and handle invalid data.
        port_table["Current Price"] = pd.to_numeric(
            port_table["Current Price"], errors="coerce"
        )
        port_table["Cost Basis"] = pd.to_numeric(
            port_table["Cost Basis"], errors="coerce"
        )
        port_table["Pct Change"] = (
            (port_table["Current Price"] - port_table["Cost Basis"]) / port_table["Cost Basis"]
        ) * 100
        port_table["Pct Change"] = pd.to_numeric(
            port_table["Pct Change"], errors="coerce"
        )
        invalid = port_table["Pct Change"].isna()
        if invalid.any():
            missing = ", ".join(port_table.loc[invalid, "Ticker"].astype(str))
            st.warning(f"Unable to compute Pct Change for: {missing}")
        port_table["Pct Change"] = port_table["Pct Change"].round(2)

        def highlight_pct(val: float) -> str:
            """Colour cells when price moved more than ±5%."""

            if val > 5:
                return "background-color: #d4ffd4"  # light green
            if val < -5:
                return "background-color: #ffd4d4"  # light red
            return ""

        st.dataframe(port_table.style.applymap(highlight_pct, subset=["Pct Change"]))
        st.caption(f"Last updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    show_buy_form()
    show_sell_form()

    # ------------------------------------------------------------------
    # Section 3: Daily Summary
    # ------------------------------------------------------------------
    st.subheader("Daily Summary")
    if st.button("Generate Daily Summary"):
        if not summary_df.empty:
            totals = summary_df[summary_df["Ticker"] == "TOTAL"].iloc[0]
            summary_md = (
                "### Today's totals:\n"
                f"- Total stock value: ${totals['Total Value']}\n"
                f"- Total PnL: ${totals['PnL']}\n"
                f"- Cash balance: ${totals['Cash Balance']}\n"
                f"- Total equity: ${totals['Total Equity']}\n"
            )
            st.markdown(summary_md)
        else:
            st.info("No summary available.")


if __name__ == "__main__":
    main()
