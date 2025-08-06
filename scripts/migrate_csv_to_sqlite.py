"""Migration script to import existing CSV data into the SQLite database."""
import pandas as pd

from config import (
    PORTFOLIO_CSV,
    TRADE_LOG_CSV,
    COL_TICKER,
    COL_SHARES,
    COL_STOP,
    COL_PRICE,
    COL_COST,
)
from portfolio import ensure_schema
from data.db import init_db, get_connection


def migrate() -> None:
    init_db()
    with get_connection() as conn:
        if PORTFOLIO_CSV.exists():
            df_port = pd.read_csv(PORTFOLIO_CSV)
            if not df_port.empty:
                # Store full history
                df_port.to_sql("portfolio_history", conn, if_exists="append", index=False)

                # Derive latest holdings and cash
                non_total = df_port[df_port["Ticker"] != "TOTAL"].copy()
                if not non_total.empty:
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
                    portfolio_df = ensure_schema(latest).reset_index(drop=True)
                    conn.execute("DELETE FROM portfolio")
                    portfolio_df.to_sql("portfolio", conn, if_exists="append", index=False)

                total_rows = df_port[df_port["Ticker"] == "TOTAL"].copy()
                if not total_rows.empty:
                    total_rows["Date"] = pd.to_datetime(total_rows["Date"])
                    cash = float(total_rows.sort_values("Date").iloc[-1]["Cash Balance"])
                    conn.execute(
                        "INSERT OR REPLACE INTO cash (id, balance) VALUES (0, ?)", (cash,)
                    )

        if TRADE_LOG_CSV.exists():
            df_log = pd.read_csv(TRADE_LOG_CSV)
            if not df_log.empty:
                df_log.to_sql("trade_log", conn, if_exists="append", index=False)


if __name__ == "__main__":
    migrate()
    print("Migration complete.")
