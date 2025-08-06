import pandas as pd

from config import PORTFOLIO_CSV, TODAY, COL_TICKER, COL_SHARES, COL_STOP, COL_PRICE, COL_COST
from portfolio import ensure_schema
from services.market import fetch_prices


def load_portfolio() -> tuple[pd.DataFrame, float, bool]:
    """Return the latest portfolio and cash balance."""

    empty_portfolio = pd.DataFrame(columns=ensure_schema(pd.DataFrame()).columns)

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
                "Ticker": COL_TICKER,
                "Shares": COL_SHARES,
                "Stop Loss": COL_STOP,
                "Cost Basis": COL_PRICE,
            },
            inplace=True,
        )
        latest[COL_COST] = latest[COL_SHARES] * latest[COL_PRICE]
        portfolio = ensure_schema(latest).reset_index(drop=True)

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
    if PORTFOLIO_CSV.exists():
        existing = pd.read_csv(PORTFOLIO_CSV)
        existing = existing[existing["Date"] != TODAY]
        df = pd.concat([existing, df], ignore_index=True)
    df.to_csv(PORTFOLIO_CSV, index=False)
    return df
