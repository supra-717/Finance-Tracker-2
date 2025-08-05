import pandas as pd
import streamlit as st
import yfinance as yf
from datetime import datetime
from pathlib import Path

# -----------------------------------------------------------------------------
# File locations
# -----------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "Scripts and CSV Files"
PORTFOLIO_CSV = DATA_DIR / "chatgpt_portfolio_update.csv"
TRADE_LOG_CSV = DATA_DIR / "chatgpt_trade_log.csv"

# Today's date used for all new logs
TODAY = datetime.today().strftime("%Y-%m-%d")

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def load_portfolio() -> tuple[pd.DataFrame, float, bool]:
    """Return latest portfolio, cash balance and whether initialization is needed.

    The boolean flag indicates if the CSV is missing, empty, or lacks a cash
    balance (i.e. first-time use) so the UI can prompt for a starting amount.
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
            columns={"Ticker": "ticker", "Shares": "shares", "Stop Loss": "stop_loss", "Cost Basis": "buy_price"},
            inplace=True,
        )
        latest["cost_basis"] = latest["shares"] * latest["buy_price"]
        portfolio = latest[["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]].reset_index(drop=True)

    total_rows = df[df["Ticker"] == "TOTAL"].copy()
    if total_rows.empty:
        cash = 0.0
        return portfolio, cash, True

    total_rows["Date"] = pd.to_datetime(total_rows["Date"])
    cash = float(total_rows.sort_values("Date").iloc[-1]["Cash Balance"])

    return portfolio, cash, False

def save_portfolio_snapshot(portfolio: pd.DataFrame, cash: float) -> pd.DataFrame:
    """Recalculate today's portfolio values and store them in ``PORTFOLIO_CSV``."""
    results = []
    total_value = 0.0
    total_pnl = 0.0

    for _, row in portfolio.iterrows():
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

def manual_buy(
    ticker: str,
    shares: float,
    price: float,
    stop_loss: float,
    portfolio: pd.DataFrame,
    cash: float,
) -> tuple[bool, str, pd.DataFrame, float]:
    """Execute a manual buy and update portfolio and logs."""
    ticker = ticker.upper()
    try:
        data = yf.download(ticker, period="1d", progress=False)
    except Exception as exc:  # pragma: no cover - network errors
        return False, f"Data download failed: {exc}", portfolio, cash
    if data.empty:
        return False, "No market data available.", portfolio, cash
    day_high = float(data["High"].iloc[-1])
    day_low = float(data["Low"].iloc[-1])
    if not (day_low <= price <= day_high):
        return False, f"Price outside today's range {day_low:.2f}-{day_high:.2f}", portfolio, cash
    cost = price * shares
    if cost > cash:
        return False, "Insufficient cash for this trade.", portfolio, cash

    log = {
        "Date": TODAY,
        "Ticker": ticker,
        "Shares Bought": shares,
        "Buy Price": price,
        "Cost Basis": cost,
        "PnL": 0.0,
        "Reason": "MANUAL BUY - New position",
    }
    if TRADE_LOG_CSV.exists():
        df = pd.read_csv(TRADE_LOG_CSV)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(TRADE_LOG_CSV, index=False)

    mask = portfolio["ticker"] == ticker
    if not mask.any():
        new_row = {
            "ticker": ticker,
            "shares": shares,
            "stop_loss": stop_loss,
            "buy_price": price,
            "cost_basis": cost,
        }
        portfolio = pd.concat([portfolio, pd.DataFrame([new_row])], ignore_index=True)
    else:
        idx = portfolio[mask].index[0]
        current_shares = float(portfolio.at[idx, "shares"])
        current_cost_basis = float(portfolio.at[idx, "cost_basis"])
        portfolio.at[idx, "shares"] = current_shares + shares
        portfolio.at[idx, "cost_basis"] = current_cost_basis + cost
        portfolio.at[idx, "buy_price"] = portfolio.at[idx, "cost_basis"] / portfolio.at[idx, "shares"]
        portfolio.at[idx, "stop_loss"] = stop_loss

    cash -= cost
    save_portfolio_snapshot(portfolio, cash)
    return True, f"Bought {shares} shares of {ticker} at ${price:.2f}.", portfolio, cash

def manual_sell(
    ticker: str,
    shares: float,
    price: float,
    portfolio: pd.DataFrame,
    cash: float,
) -> tuple[bool, str, pd.DataFrame, float]:
    """Execute a manual sell and update portfolio and logs."""
    ticker = ticker.upper()
    if ticker not in portfolio["ticker"].values:
        return False, "Ticker not in portfolio.", portfolio, cash
    try:
        data = yf.download(ticker, period="1d", progress=False)
    except Exception as exc:  # pragma: no cover - network errors
        return False, f"Data download failed: {exc}", portfolio, cash
    if data.empty:
        return False, "No market data available.", portfolio, cash
    day_high = float(data["High"].iloc[-1])
    day_low = float(data["Low"].iloc[-1])
    if not (day_low <= price <= day_high):
        return False, f"Price outside today's range {day_low:.2f}-{day_high:.2f}", portfolio, cash

    row = portfolio[portfolio["ticker"] == ticker].iloc[0]
    total_shares = float(row["shares"])
    if shares > total_shares:
        return False, f"Trying to sell {shares} shares but only own {total_shares}.", portfolio, cash
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
    if TRADE_LOG_CSV.exists():
        df = pd.read_csv(TRADE_LOG_CSV)
        df = pd.concat([df, pd.DataFrame([log])], ignore_index=True)
    else:
        df = pd.DataFrame([log])
    df.to_csv(TRADE_LOG_CSV, index=False)

    if shares == total_shares:
        portfolio = portfolio[portfolio["ticker"] != ticker]
    else:
        idx = portfolio[portfolio["ticker"] == ticker].index[0]
        portfolio.at[idx, "shares"] = total_shares - shares
        portfolio.at[idx, "cost_basis"] = portfolio.at[idx, "shares"] * buy_price

    cash += price * shares
    save_portfolio_snapshot(portfolio, cash)
    return True, f"Sold {shares} shares of {ticker} at ${price:.2f}.", portfolio, cash

# -----------------------------------------------------------------------------
# Streamlit UI
# -----------------------------------------------------------------------------

st.title("ChatGPT Portfolio Manager")

if "portfolio" not in st.session_state:
    port, cash, needs_cash = load_portfolio()
    st.session_state.portfolio = port
    st.session_state.cash = cash
    st.session_state.needs_cash = needs_cash

if st.session_state.get("needs_cash", False):
    # Prompt for starting cash on first-time use
    st.subheader("Initialize Portfolio")
    with st.form("init_cash_form"):
        start_cash = st.number_input("Enter starting cash", min_value=0.0, format="%.2f")
        init_submit = st.form_submit_button("Set Starting Cash")
    if init_submit:
        st.session_state.cash = start_cash
        st.session_state.needs_cash = False
        # Persist the cash value to CSV
        save_portfolio_snapshot(st.session_state.portfolio, st.session_state.cash)
        st.success(f"Starting cash of ${start_cash:.2f} recorded.")
        st.rerun()
else:
    # Always refresh today's snapshot and totals once cash is initialized
    summary_df = save_portfolio_snapshot(st.session_state.portfolio, st.session_state.cash)

    st.subheader("Current Portfolio")
    if st.session_state.portfolio.empty:
        st.info("Your portfolio is empty. Add your first trade below.")
    else:
        st.dataframe(st.session_state.portfolio)
    st.metric("Cash Balance", f"${st.session_state.cash:.2f}")

    st.subheader("Log a Buy")
    with st.form("buy_form"):
        b_ticker = st.text_input("Ticker")
        b_shares = st.number_input("Shares", min_value=0.0, step=1.0)
        b_price = st.number_input("Price", min_value=0.0, format="%.2f")
        b_stop = st.number_input("Stop-loss", min_value=0.0, format="%.2f")
        b_submit = st.form_submit_button("Submit Buy")
    if b_submit:
        ok, msg, port, cash = manual_buy(
            b_ticker, b_shares, b_price, b_stop, st.session_state.portfolio, st.session_state.cash
        )
        if ok:
            st.session_state.portfolio = port
            st.session_state.cash = cash
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.subheader("Log a Sell")
    with st.form("sell_form"):
        s_ticker = st.text_input("Ticker", key="sell_ticker")
        s_shares = st.number_input("Shares", min_value=0.0, step=1.0, key="sell_shares")
        s_price = st.number_input("Price", min_value=0.0, format="%.2f", key="sell_price")
        s_submit = st.form_submit_button("Submit Sell")
    if s_submit:
        ok, msg, port, cash = manual_sell(
            s_ticker, s_shares, s_price, st.session_state.portfolio, st.session_state.cash
        )
        if ok:
            st.session_state.portfolio = port
            st.session_state.cash = cash
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.subheader("Daily Summary")
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
