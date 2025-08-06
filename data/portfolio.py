import pandas as pd

from config import TODAY, COL_TICKER, COL_SHARES, COL_STOP, COL_PRICE, COL_COST
from portfolio import ensure_schema
from services.market import fetch_prices
from data.db import init_db, get_connection


def load_portfolio() -> tuple[pd.DataFrame, float, bool]:
    """Return the latest portfolio and cash balance."""

    empty_portfolio = pd.DataFrame(columns=ensure_schema(pd.DataFrame()).columns)

    init_db()
    with get_connection() as conn:
        portfolio_df = pd.read_sql_query("SELECT * FROM portfolio", conn)
        cash_row = conn.execute("SELECT balance FROM cash WHERE id = 0").fetchone()

    if portfolio_df.empty and cash_row is None:
        return empty_portfolio, 0.0, True

    portfolio = ensure_schema(portfolio_df) if not portfolio_df.empty else empty_portfolio
    cash = float(cash_row[0]) if cash_row else 0.0
    return portfolio, cash, portfolio_df.empty


def save_portfolio_snapshot(portfolio_df: pd.DataFrame, cash: float) -> pd.DataFrame:
    """Recalculate today's portfolio values and persist them to ``PORTFOLIO_CSV``."""

    results: list[dict[str, float | str]] = []
    total_value = 0.0
    total_pnl = 0.0

    tickers = portfolio_df[COL_TICKER].tolist()
    data = fetch_prices(tickers)
    prices: dict[str, float] = {t: 0.0 for t in tickers}
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"].iloc[-1]
            for t in tickers:
                val = close.get(t)
                if val is not None and not pd.isna(val):
                    prices[t] = float(val)
        else:
            val = data["Close"].iloc[-1]
            if tickers and not pd.isna(val):
                prices[tickers[0]] = float(val)

    for _, row in portfolio_df.iterrows():
        ticker = row[COL_TICKER]
        shares = float(row[COL_SHARES])
        stop = float(row[COL_STOP])
        buy_price = float(row[COL_PRICE])

        price = prices.get(ticker, 0.0)
        value = round(price * shares, 2)
        pnl = round((price - buy_price) * shares, 2)
        total_value += value
        total_pnl += pnl

        results.append(
            {
                "Date": TODAY,
                "Ticker": ticker,
                "Shares": shares,
                "Cost Basis": buy_price,
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

    # Rename columns to match the portfolio_history table schema
    df = df.rename(
        columns={
            "Date": "date",
            "Ticker": "ticker",
            "Shares": "shares",
            "Cost Basis": "cost_basis",
            "Stop Loss": "stop_loss",
            "Current Price": "current_price",
            "Total Value": "total_value",
            "PnL": "pnl",
            "Action": "action",
            "Cash Balance": "cash_balance",
            "Total Equity": "total_equity",
        }
    )

    # Ensure column order aligns with the database schema
    df = df[
        [
            "date",
            "ticker",
            "shares",
            "cost_basis",
            "stop_loss",
            "current_price",
            "total_value",
            "pnl",
            "action",
            "cash_balance",
            "total_equity",
        ]
    ]

    init_db()
    with get_connection() as conn:
        # Update current holdings
        conn.execute("DELETE FROM portfolio")
        portfolio_df.to_sql("portfolio", conn, if_exists="append", index=False)

        # Update cash balance (single row table)
        conn.execute("INSERT OR REPLACE INTO cash (id, balance) VALUES (0, ?)", (cash,))

        # Store daily snapshot
        conn.execute("DELETE FROM portfolio_history WHERE date = ?", (TODAY,))
        df.to_sql("portfolio_history", conn, if_exists="append", index=False)

    return df
