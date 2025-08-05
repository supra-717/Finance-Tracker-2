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

def load_portfolio() -> tuple[pd.DataFrame, float]:
    """Return latest portfolio and cash balance from ``PORTFOLIO_CSV``."""
    if not PORTFOLIO_CSV.exists():
        return pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]), 0.0

    df = pd.read_csv(PORTFOLIO_CSV)
    non_total = df[df["Ticker"] != "TOTAL"].copy()
    if non_total.empty:
        portfolio = pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"])
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
    else:
        total_rows["Date"] = pd.to_datetime(total_rows["Date"])
        cash = float(total_rows.sort_values("Date").iloc[-1]["Cash Balance"])

    return portfolio, cash

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
    st.session_state.portfolio, st.session_state.cash = load_portfolio()

# Always refresh today's snapshot and totals
summary_df = save_portfolio_snapshot(st.session_state.portfolio, st.session_state.cash)

st.subheader("Current Portfolio")
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
    ok, msg, port, cash = manual_buy(b_ticker, b_shares, b_price, b_stop, st.session_state.portfolio, st.session_state.cash)
    if ok:
        st.session_state.portfolio = port
        st.session_state.cash = cash
        st.success(msg)
        st.experimental_rerun()
    else:
        st.error(msg)

st.subheader("Log a Sell")
with st.form("sell_form"):
    s_ticker = st.text_input("Ticker", key="sell_ticker")
    s_shares = st.number_input("Shares", min_value=0.0, step=1.0, key="sell_shares")
    s_price = st.number_input("Price", min_value=0.0, format="%.2f", key="sell_price")
    s_submit = st.form_submit_button("Submit Sell")
if s_submit:
    ok, msg, port, cash = manual_sell(s_ticker, s_shares, s_price, st.session_state.portfolio, st.session_state.cash)
    if ok:
        st.session_state.portfolio = port
        st.session_state.cash = cash
        st.success(msg)
        st.experimental_rerun()
    else:
        st.error(msg)

st.subheader("Daily Summary")
st.dataframe(summary_df)
if not summary_df.empty:
    totals = summary_df[summary_df["Ticker"] == "TOTAL"].iloc[0]
    st.write(f"Total Stock Value: ${totals['Total Value']}")
    st.write(f"PnL: ${totals['PnL']}")
    st.write(f"Total Equity: ${totals['Total Equity']}")
