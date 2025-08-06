import pandas as pd

from config import (
    TODAY,
    COL_TICKER,
    COL_SHARES,
    COL_STOP,
    COL_PRICE,
    COL_COST,
)
from data.portfolio import save_portfolio_snapshot
from services.market import get_day_high_low
from services.logging import log_error
from data.db import init_db, get_connection


def append_trade_log(log: dict) -> None:
    """Persist a dictionary entry to the trade log table."""

    init_db()
    with get_connection() as conn:
        df = pd.DataFrame([log])
        df = df.rename(
            columns={
                "Date": "date",
                "Ticker": "ticker",
                "Shares Bought": "shares_bought",
                "Buy Price": "buy_price",
                "Cost Basis": "cost_basis",
                "PnL": "pnl",
                "Reason": "reason",
                "Shares Sold": "shares_sold",
                "Sell Price": "sell_price",
            }
        )
        df.to_sql("trade_log", conn, if_exists="append", index=False)


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
    if shares <= 0 or price <= 0:
        msg = "Shares and price must be positive."
        log_error(msg)
        return False, msg, portfolio_df, cash
    try:
        day_high, day_low = get_day_high_low(ticker)
    except Exception as exc:  # pragma: no cover - network errors
        log_error(str(exc))
        return False, str(exc), portfolio_df, cash

    if not (day_low <= price <= day_high):
        msg = f"Price outside today's range {day_low:.2f}-{day_high:.2f}"
        log_error(msg)
        return False, msg, portfolio_df, cash

    cost = price * shares
    if cost > cash:
        log_error("Insufficient cash for this trade.")
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

    mask = portfolio_df[COL_TICKER] == ticker
    if not mask.any():
        new_row = {
            COL_TICKER: ticker,
            COL_SHARES: shares,
            COL_STOP: stop_loss,
            COL_PRICE: price,
            COL_COST: cost,
        }
        portfolio_df = pd.concat(
            [portfolio_df, pd.DataFrame([new_row])], ignore_index=True
        )
    else:
        idx = portfolio_df[mask].index[0]
        current_shares = float(portfolio_df.at[idx, COL_SHARES])
        current_cost = float(portfolio_df.at[idx, COL_COST])
        portfolio_df.at[idx, COL_SHARES] = current_shares + shares
        portfolio_df.at[idx, COL_COST] = current_cost + cost
        portfolio_df.at[idx, COL_PRICE] = (
            portfolio_df.at[idx, COL_COST] / portfolio_df.at[idx, COL_SHARES]
        )
        portfolio_df.at[idx, COL_STOP] = stop_loss

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
    if shares <= 0 or price <= 0:
        msg = "Shares and price must be positive."
        log_error(msg)
        return False, msg, portfolio_df, cash
    if ticker not in portfolio_df[COL_TICKER].values:
        msg = "Ticker not in portfolio."
        log_error(msg)
        return False, msg, portfolio_df, cash

    try:
        day_high, day_low = get_day_high_low(ticker)
    except Exception as exc:  # pragma: no cover - network errors
        log_error(str(exc))
        return False, str(exc), portfolio_df, cash

    if not (day_low <= price <= day_high):
        msg = f"Price outside today's range {day_low:.2f}-{day_high:.2f}"
        log_error(msg)
        return False, msg, portfolio_df, cash

    row = portfolio_df[portfolio_df[COL_TICKER] == ticker].iloc[0]
    total_shares = float(row[COL_SHARES])
    if shares > total_shares:
        msg = f"Trying to sell {shares} shares but only own {total_shares}."
        log_error(msg)
        return False, msg, portfolio_df, cash

    buy_price = float(row[COL_PRICE])
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
        portfolio_df = portfolio_df[portfolio_df[COL_TICKER] != ticker]
    else:
        idx = portfolio_df[portfolio_df[COL_TICKER] == ticker].index[0]
        portfolio_df.at[idx, COL_SHARES] = total_shares - shares
        portfolio_df.at[idx, COL_COST] = portfolio_df.at[idx, COL_SHARES] * buy_price

    cash += price * shares
    save_portfolio_snapshot(portfolio_df, cash)
    msg = f"Sold {shares} shares of {ticker} at ${price:.2f}."
    return True, msg, portfolio_df, cash
