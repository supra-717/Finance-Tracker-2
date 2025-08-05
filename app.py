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
    }.items():
        st.session_state.setdefault(key, default)

    if "portfolio" not in st.session_state:
        port, cash, needs_cash = load_portfolio()
        st.session_state.portfolio = port
        st.session_state.cash = cash
        st.session_state.needs_cash = needs_cash


def show_buy_form() -> None:
    """Render and process the buy form."""

    st.subheader("Log a Buy")
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
            st.session_state.feedback = ("success", msg)
            # Remove widget state keys so ``init_session_state``
            # reinitialises them on the next rerun.  This clears the
            # form fields without setting values for widgets that are
            # currently in use, avoiding StreamlitAPIException.
            for key in ("b_ticker", "b_shares", "b_price", "b_stop"):
                st.session_state.pop(key, None)
        else:
            st.session_state.feedback = ("error", msg)

    with st.form("buy_form"):
        st.text_input("Ticker", key="b_ticker")
        st.number_input("Shares", min_value=0.0, step=1.0, key="b_shares")
        st.number_input("Price", min_value=0.0, format="%.2f", key="b_price")
        st.number_input("Stop-loss", min_value=0.0, format="%.2f", key="b_stop")
        # Use ``on_click`` callback so state mutations occur in the
        # callback rather than in-line after widget definition.
        st.form_submit_button("Submit Buy", on_click=submit_buy)


def show_sell_form() -> None:
    """Render and process the sell form."""

    st.subheader("Log a Sell")
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
            # Remove widget state keys for a clean form next run.
            for key in ("s_ticker", "s_shares", "s_price"):
                st.session_state.pop(key, None)
        else:
            st.session_state.feedback = ("error", msg)

    with st.form("sell_form"):
        st.text_input("Ticker", key="s_ticker")
        st.number_input("Shares", min_value=0.0, step=1.0, key="s_shares")
        st.number_input("Price", min_value=0.0, format="%.2f", key="s_price")
        # Trigger callback to perform sell and clear state safely.
        st.form_submit_button("Submit Sell", on_click=submit_sell)


def main() -> None:
    """Entry point for the Streamlit UI."""

    st.title("ChatGPT Portfolio Manager")

    # Display feedback messages once and remove from session state so they
    # do not linger between reruns.
    feedback = st.session_state.pop("feedback", None)
    if feedback:
        kind, text = feedback
        if kind == "success":
            st.success(text)
        else:
            st.error(text)

    init_session_state()

    if st.session_state.get("needs_cash", False):
        # Prompt for starting cash on first-time use
        st.subheader("Initialize Portfolio")
        with st.form("init_cash_form"):
            start_cash = st.number_input(
                "Enter starting cash", min_value=0.0, format="%.2f"
            )
            init_submit = st.form_submit_button("Set Starting Cash")
        if init_submit:
            st.session_state.cash = start_cash
            st.session_state.needs_cash = False
            save_portfolio_snapshot(
                st.session_state.portfolio, st.session_state.cash
            )
            st.success(f"Starting cash of ${start_cash:.2f} recorded.")
            st.rerun()
        return

    # Always refresh today's snapshot and totals once cash is initialised
    summary_df = save_portfolio_snapshot(
        st.session_state.portfolio, st.session_state.cash
    )

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

    st.subheader("Current Portfolio")
    if st.session_state.portfolio.empty:
        st.info("Your portfolio is empty. Add your first trade below.")
    else:
        st.dataframe(st.session_state.portfolio)
    st.metric("Cash Balance", f"${st.session_state.cash:.2f}")

    show_buy_form()
    show_sell_form()


if __name__ == "__main__":
    main()
