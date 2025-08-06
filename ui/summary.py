import pandas as pd
import streamlit as st

from config import TODAY
from services.market import fetch_price


def build_daily_summary(summary_df: pd.DataFrame) -> str:
    """Return a markdown summary of the portfolio and watchlist."""

    totals = summary_df[summary_df["Ticker"] == "TOTAL"].iloc[0]
    holdings = summary_df[summary_df["Ticker"] != "TOTAL"].copy()
    holdings = holdings[
        ["Ticker", "Shares", "Cost Basis", "Current Price", "Stop Loss", "Total Value", "PnL"]
    ].rename(
        columns={
            "Cost Basis": "Buy Price",
            "Stop Loss": "Stop-Loss",
            "Total Value": "Value",
        }
    )
    for col in ["Buy Price", "Current Price", "Stop-Loss", "Value", "PnL"]:
        holdings[col] = pd.to_numeric(holdings[col], errors="coerce").round(2)
    holdings_md = holdings.to_markdown(index=False) if not holdings.empty else "None"

    gainer = loser = "None"
    if not holdings.empty:
        gain_row = holdings.loc[holdings["PnL"].idxmax()]
        if gain_row["PnL"] > 0:
            gainer = f"{gain_row['Ticker']} (${gain_row['PnL']:.2f})"
        lose_row = holdings.loc[holdings["PnL"].idxmin()]
        if lose_row["PnL"] < 0:
            loser = f"{lose_row['Ticker']} (${lose_row['PnL']:.2f})"

    watch_rows = []
    for t in st.session_state.watchlist:
        price = st.session_state.watchlist_prices.get(t)
        if price is None:
            price = fetch_price(t)
            st.session_state.watchlist_prices[t] = price
        price_str = f"${price:.2f}" if price is not None else "N/A"
        watch_rows.append((t, price_str))
    watch_md = (
        "|Ticker|Price|\n|---|---|\n" + "\n".join(f"|{t}|{p}|" for t, p in watch_rows)
        if watch_rows
        else "None"
    )

    prompt = (
        "Reevaluate your portfolio. Research the current market and decide if you would "
        "like to add or drop any stocks or adjust. Remember, you have complete control "
        "over your portfolio. Only trade micro-caps."
    )

    summary_md = (
        f"## Daily Portfolio Summary - {TODAY}\n\n"
        f"**Cash balance:** ${totals['Cash Balance']:.2f}\n\n"
        "### Holdings\n"
        f"{holdings_md}\n\n"
        f"**Total equity:** ${totals['Total Equity']:.2f}\n\n"
        f"**Largest gainer:** {gainer}\n"
        f"**Largest loser:** {loser}\n\n"
        "### Watchlist\n"
        f"{watch_md}\n\n"
        f"{prompt}"
    )

    return summary_md
