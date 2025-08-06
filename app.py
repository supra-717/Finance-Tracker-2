"""Streamlit app for local portfolio tracking and AI‑assisted trading.

The original implementation grew organically and contained a mix of UI and
backend logic, duplicated blocks, and sparse documentation.  This refactor
tidies the structure, centralises repeated behaviours, and adds explicit
docstrings and inline comments to make the application easier for developers
to understand and extend.
"""

from datetime import datetime
from pathlib import Path
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

from portfolio import PORTFOLIO_COLUMNS, ensure_schema

# ---------------------------------------------------------------------------
# Configuration & constants
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Assisted Trading")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Centralised file locations
PORTFOLIO_CSV = DATA_DIR / "chatgpt_portfolio_update.csv"
TRADE_LOG_CSV = DATA_DIR / "chatgpt_trade_log.csv"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"

# Column keys for easy reference in the UI logic
COL_TICKER, COL_SHARES, COL_STOP, COL_PRICE, COL_COST = PORTFOLIO_COLUMNS

# Today's date used for all new logs.
TODAY = datetime.today().strftime("%Y-%m-%d")


def log_error(message: str) -> None:
    """Append ``message`` to a session-scoped error log."""

    st.session_state.setdefault("error_log", []).append(
        f"{datetime.now():%H:%M:%S} - {message}"
    )


def clear_inputs_on_focus(labels: list[str]) -> None:
    """Attach JS to clear inputs matching ``labels`` when focused."""

    script_parts = []
    for idx, label in enumerate(labels):
        script_parts.append(
            f"""
            const els{idx} = parent.document.querySelectorAll('input[aria-label="{label}"]');
            els{idx}.forEach((el) => {{
                el.addEventListener('focus', () => {{
                    if (el.value !== '') {{
                        el.value = '';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }});
            }});
            """
        )
    components.html(f"<script>{''.join(script_parts)}</script>", height=0)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_watchlist() -> list[str]:
    """Return saved watchlist tickers from ``WATCHLIST_FILE``.

    The file stores a simple JSON list.  Any problems reading the file result
    in an empty list so the UI can proceed without crashing.
    """

    if WATCHLIST_FILE.exists():
        try:
            data = json.loads(WATCHLIST_FILE.read_text())
            return [str(t).upper() for t in data if isinstance(t, str)]
        except Exception:
            pass
    return []


def save_watchlist(tickers: list[str]) -> None:
    """Persist ``tickers`` to ``WATCHLIST_FILE`` as JSON."""

    try:
        WATCHLIST_FILE.write_text(json.dumps(tickers))
    except Exception:
        # Persistence failures shouldn't crash the app; users can still rely on
        # session state within the current run.
        pass


@st.cache_data(ttl=300)
def fetch_price(ticker: str) -> float | None:
    """Return the latest close price for ``ticker`` or ``None`` on failure.

    Results are cached for a short period to avoid excessive network calls
    when the same ticker is requested repeatedly.
    """

    try:  # pragma: no cover - network errors
        data = yf.download(ticker, period="1d", progress=False)
        return float(data["Close"].iloc[-1]) if not data.empty else None
    except Exception:
        log_error(f"Failed to fetch price for {ticker}")
        return None

def load_portfolio() -> tuple[pd.DataFrame, float, bool]:
    """Return the latest portfolio and cash balance.

    The boolean flag indicates whether initialisation is required (e.g. the CSV
    is missing or lacks a cash balance) so the UI can prompt the user for a
    starting amount.
    """

    empty_portfolio = pd.DataFrame(columns=PORTFOLIO_COLUMNS)

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

def init_session_state() -> None:
    """Initialise default values in ``st.session_state`` on first run."""

    for key, default in {
        "b_ticker": "",
        "b_shares": 0.0,
        "b_price": 0.0,
        # Percentage below the buy price to place a stop loss.
        "b_stop_pct": 0.0,
        "s_ticker": "",
        "s_shares": 0.0,
        "s_price": 0.0,
        "ac_amount": 0.0,
        "lookup_symbol": "",
        # Holds error text for symbol lookup so it can be cleared on success.
        "lookup_error": "",
        # Feedback messages related to watchlist actions shown in sidebar.
        "watchlist_feedback": None,
        "watchlist": [],
        # Cache of latest watchlist prices fetched via the refresh button.
        "watchlist_prices": {},
        # Toggle for showing the inline "Add Cash" form.
        "show_cash_form": False,
        # Daily summary text and visibility toggle.
        "daily_summary": "",
        "summary_visible": False,
    }.items():
        st.session_state.setdefault(key, default)

    if "portfolio" not in st.session_state:
        port, cash, needs_cash = load_portfolio()
        st.session_state.portfolio = port
        st.session_state.cash = cash
        st.session_state.needs_cash = needs_cash

    # Load a persisted watchlist from disk only on first run.
    if not st.session_state.watchlist and WATCHLIST_FILE.exists():
        st.session_state.watchlist = load_watchlist()


def show_onboarding() -> None:
    """Display a simple onboarding message for first-time users."""

    if not st.session_state.get("dismissed_onboarding"):
        def dismiss() -> None:
            st.session_state.dismissed_onboarding = True
            st.rerun()

        st.info(
            "Use the controls below to manage your portfolio. "
            "Data is stored in the local `data/` directory."
        )
        st.button("Dismiss", key="dismiss_onboard", on_click=dismiss)


def dismiss_summary() -> None:
    """Hide the daily summary and immediately rerun the app."""

    st.session_state.summary_visible = False
    st.rerun()


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
        # Clear field and any error so the next lookup starts fresh.
        st.session_state.lookup_symbol = ""
        st.session_state.lookup_error = ""

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
        save_watchlist(st.session_state.watchlist)
        st.session_state.watchlist_feedback = (
            "info",
            f"Removed {', '.join(removed)} from watchlist (now in portfolio).",
        )

    # Lookup form for a single ticker symbol.
    # Slot to show a lookup error message if the symbol fails to resolve.
    error_slot = sidebar.empty()
    symbol = sidebar.text_input("Symbol", key="lookup_symbol", placeholder="e.g. AAPL")
    if symbol:
        sym = symbol.upper()
        price = fetch_price(sym)
        if price is None:
            st.session_state.lookup_error = "Ticker not found."
        else:
            # Clear any previous errors on successful lookup.
            st.session_state.lookup_error = ""
            ticker_obj = yf.Ticker(sym)
            name = ticker_obj.info.get("shortName") or ticker_obj.info.get("longName") or sym
            sidebar.write(f"{name}: ${price:.2f}")
            sidebar.button(
                "Add to Watchlist",
                key="add_watchlist",
                on_click=add_watchlist_and_clear,
                args=(sym, price, portfolio_tickers),
            )
    else:
        # No symbol entered: clear any stale errors.
        st.session_state.lookup_error = ""

    if st.session_state.lookup_error:
        error_slot.error(st.session_state.lookup_error)

    if st.session_state.watchlist:
        # Header with refresh icon to update all prices.
        header = sidebar.container()
        hcol1, hcol2 = header.columns([4, 1])
        hcol1.subheader("Watchlist")
        if hcol2.button("🔄", key="refresh_watchlist", help="Refresh prices"):
            updated: dict[str, float | None] = {}
            for t in st.session_state.watchlist:
                updated[t] = fetch_price(t)
            st.session_state.watchlist_prices.update(updated)

        # CSS to render remove buttons as red circular Xs.
        sidebar.markdown(
            """
            <style>
            .watchlist-item {display:flex; justify-content:space-between; align-items:center;}
            .watchlist-item button {
                color:white; background-color:red; border:none; border-radius:50%;
                width:1.2em; height:1.2em; padding:0; line-height:1.2em;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        for t in st.session_state.watchlist.copy():
            price = st.session_state.watchlist_prices.get(t)
            display_price = f"${price:.2f}" if price is not None else "N/A"
            item = sidebar.container()
            item.markdown("<div class='watchlist-item'>", unsafe_allow_html=True)
            col1, col2 = item.columns([4, 1])
            col1.write(f"{t}: {display_price}")
            if col2.button("✖", key=f"rm_{t}", help="Remove"):
                st.session_state.watchlist.remove(t)
                st.session_state.watchlist_prices.pop(t, None)
                save_watchlist(st.session_state.watchlist)
                st.session_state.watchlist_feedback = ("info", f"{t} removed from watchlist.")
                st.rerun()
            item.markdown("</div>", unsafe_allow_html=True)

    feedback = st.session_state.pop("watchlist_feedback", None)
    if feedback:
        kind, text = feedback
        if kind == "success":
            feedback_slot.success(text)
        elif kind == "error":
            feedback_slot.error(text)
        else:
            feedback_slot.info(text)


def show_buy_form() -> None:
    """Render and process the buy form inside an expander."""

    def submit_buy() -> None:
        """Handle Buy submission and reset the form via callback."""

        stop_price = 0.0
        if st.session_state.b_stop_pct > 0:
            stop_price = st.session_state.b_price * (
                1 - st.session_state.b_stop_pct / 100
            )

        ok, msg, port, cash = manual_buy(
            st.session_state.b_ticker,
            st.session_state.b_shares,
            st.session_state.b_price,
            stop_price,
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
                save_watchlist(st.session_state.watchlist)
                msg += f" {ticker} removed from watchlist."
            st.session_state.feedback = ("success", msg)
            # Reset form fields on success so the form appears empty.
            st.session_state.b_ticker = ""
            st.session_state.b_shares = 0.0
            st.session_state.b_price = 0.0
            st.session_state.b_stop_pct = 0.0
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Buy"):
        with st.form("buy_form", clear_on_submit=True):
            ticker = st.text_input("Ticker", key="b_ticker")
            st.number_input("Shares", min_value=0.0, step=1.0, key="b_shares")

            latest = fetch_price(ticker) if ticker else 0.0
            st.number_input(
                "Price", min_value=0.0, format="%.2f", key="b_price", value=latest or 0.0
            )

            st.number_input(
                "Stop Loss %", min_value=0.0, format="%.1f", key="b_stop_pct"
            )
            if st.session_state.b_price > 0 and st.session_state.b_stop_pct > 0:
                calc_stop = st.session_state.b_price * (
                    1 - st.session_state.b_stop_pct / 100
                )
                st.caption(f"Stop loss price: ${calc_stop:.2f}")

            # Use ``on_click`` callback so state mutations occur in the
            # callback rather than in-line after widget definition.
            st.form_submit_button("Submit Buy", on_click=submit_buy)

    clear_inputs_on_focus(["Ticker", "Shares", "Price", "Stop Loss %"])


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
            # Clear form inputs on success.
            st.session_state.s_ticker = ""
            st.session_state.s_shares = 0.0
            st.session_state.s_price = 0.0
        else:
            st.session_state.feedback = ("error", msg)

    with st.expander("Log a Sell"):
        with st.form("sell_form", clear_on_submit=True):
            tickers = st.session_state.portfolio[COL_TICKER].tolist()
            st.selectbox("Ticker", tickers, key="s_ticker")
            st.number_input("Shares", min_value=0.0, step=1.0, key="s_shares")
            st.number_input("Price", min_value=0.0, format="%.2f", key="s_price")
            # Trigger callback to perform sell and clear state safely.
            st.form_submit_button("Submit Sell", on_click=submit_sell)

    clear_inputs_on_focus(["Shares", "Price"])


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


def show_cash_section() -> None:
    """Display cash balance and provide a toggleable form to add funds."""

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
        st.session_state.show_cash_form = False
        st.session_state.ac_amount = 0.0

    def cancel_cash() -> None:
        """Hide the add-cash form without changing the balance."""

        st.session_state.show_cash_form = False
        st.session_state.ac_amount = 0.0

    st.subheader("Cash Balance")
    # Display the current cash amount.
    st.markdown(f"<h3>${st.session_state.cash:.2f}</h3>", unsafe_allow_html=True)

    if st.session_state.show_cash_form:
        # Form appears directly under the balance when the button is clicked.
        with st.form("add_cash_form", clear_on_submit=True):
            st.number_input(
                "Amount",
                min_value=0.0,
                format="%.2f",
                key="ac_amount",
            )
            col_add, col_cancel = st.columns(2)
            col_add.form_submit_button("Add", on_click=submit_cash)
            col_cancel.form_submit_button("Cancel", on_click=cancel_cash)
    else:
        st.button(
            "Add Cash",
            on_click=lambda: st.session_state.update(show_cash_form=True),
        )


def main() -> None:
    """Entry point for the Streamlit UI."""

    init_session_state()

    header_cols = st.columns([4, 1, 1])
    header_cols[0].title("AI Assisted Trading")
    if not st.session_state.portfolio.empty:
        csv = st.session_state.portfolio.to_csv(index=False).encode("utf-8")
        header_cols[1].download_button(
            "Download Portfolio", csv, "portfolio_snapshot.csv", "text/csv"
        )
    else:
        header_cols[1].empty()
    if TRADE_LOG_CSV.exists():
        tl_df = pd.read_csv(TRADE_LOG_CSV)
        if not tl_df.empty:
            tl_csv = tl_df.to_csv(index=False).encode("utf-8")
            header_cols[2].download_button(
                "Download Trade Log", tl_csv, "trade_log.csv", "text/csv"
            )
        else:
            header_cols[2].empty()
    else:
        header_cols[2].empty()

    dashboard_tab, guide_tab = st.tabs(["Dashboard", "User Guide"])

    with dashboard_tab:
        show_watchlist_sidebar()
        show_onboarding()

        theme = st.sidebar.radio("Theme", ["Light", "Dark"], key="theme")
        if theme == "Dark":
            st.write(
                "<style>body { background-color: #0e1117; color: white; }</style>",
                unsafe_allow_html=True,
            )

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
        else:
            # Always refresh today's snapshot and totals once cash is initialised
            summary_df = save_portfolio_snapshot(
                st.session_state.portfolio, st.session_state.cash
            )

            # --------------------------------------------------------------
            # Section 1: Cash Balance & Add Cash
            # --------------------------------------------------------------
            show_cash_section()

            # --------------------------------------------------------------
            # Section 2: Current Portfolio Table
            # --------------------------------------------------------------
            port_table = summary_df[summary_df["Ticker"] != "TOTAL"].copy()
            header_cols = st.columns([8, 1, 1])
            header_cols[0].subheader("Current Portfolio")
            if port_table.empty:
                header_cols[1].empty()
                header_cols[2].empty()
                st.info(
                    "Your portfolio is empty. Use the Buy form below to add your first position."
                )
            else:
                auto_refresh = header_cols[1].checkbox(
                    "Auto Refresh", key="auto_refresh", help="Refresh every 30 min"
                )
                if header_cols[2].button(
                    "🔄", key="refresh_portfolio", help="Refresh prices"
                ):
                    st.rerun()
                if auto_refresh:
                    try:  # pragma: no cover - optional dependency
                        from streamlit_autorefresh import st_autorefresh

                        st_autorefresh(interval=30 * 60 * 1000, key="portfolio_refresh")
                    except Exception:  # pragma: no cover - import-time failure
                        st.warning(
                            "Install streamlit-autorefresh for auto refresh support."
                        )

                st.caption(
                    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # Ensure numeric types for calculations and handle invalid data.
                numeric_cols = [
                    "Shares",
                    "Cost Basis",
                    "Current Price",
                    "Stop Loss",
                    "Total Value",
                    "PnL",
                ]
                for col in numeric_cols:
                    if col in port_table.columns:
                        port_table[col] = pd.to_numeric(
                            port_table[col], errors="coerce"
                        )

                if {"Current Price", "Cost Basis"}.issubset(port_table.columns):
                    port_table["Pct Change"] = (
                        (port_table["Current Price"] - port_table["Cost Basis"])
                        / port_table["Cost Basis"]
                        * 100
                    )
                else:
                    port_table["Pct Change"] = pd.NA
                invalid = port_table["Pct Change"].isna()
                if invalid.any():
                    missing = ", ".join(
                        port_table.loc[invalid, "Ticker"].astype(str)
                    )
                    st.warning(f"Unable to compute Pct Change for: {missing}")

                # Rename and reorder columns for display
                port_table = port_table.rename(
                    columns={"Cost Basis": "Buy Price", "Total Value": "Value"}
                )
                port_table = port_table[
                    [
                        "Ticker",
                        "Shares",
                        "Buy Price",
                        "Current Price",
                        "Pct Change",
                        "Stop Loss",
                        "Value",
                        "PnL",
                        "Action",
                    ]
                ]

                required_columns = [
                    "Ticker",
                    "Shares",
                    "Buy Price",
                    "Current Price",
                    "Pct Change",
                    "Stop Loss",
                    "Value",
                    "PnL",
                    "Action",
                ]
                missing_cols = [
                    col for col in required_columns if col not in port_table.columns
                ]
                if missing_cols:
                    st.error(f"Missing columns: {', '.join(missing_cols)}")
                    st.write(port_table.head())
                else:
                    def fmt_currency(x: float) -> str:
                        return f"${x:,.2f}"

                    def fmt_percent(x: float) -> str:
                        sign = "+" if x > 0 else ""
                        arrow = "↑" if x > 0 else ("↓" if x < 0 else "")
                        return f"{sign}{x:.1f}% {arrow}".strip()

                    def fmt_shares(x: float) -> str:
                        return f"{int(x):,}"

                    def highlight_pct(val: float) -> str:
                        if val > 5:
                            return "background-color: #d4ffd4"  # light green
                        if val < -5:
                            return "background-color: #ffd4d4"  # light red
                        return ""

                    def color_pnl(val: float) -> str:
                        if val > 0:
                            return "color: green"
                        if val < 0:
                            return "color: red"
                        return ""

                    def highlight_stop(row: pd.Series) -> list[str]:
                        price = row.get("Current Price", None)
                        stop = row.get("Stop Loss", None)
                        styles = ["" for _ in row.index]
                        if (
                            price is not None
                            and stop is not None
                            and pd.notna(price)
                            and pd.notna(stop)
                            and stop > 0
                            and abs(price - stop) / stop <= 0.05
                        ):
                            idx = row.index.get_loc("Stop Loss")
                            styles[idx] = "background-color: #ffe8cc"
                        return styles

                    numeric_display = [
                        "Shares",
                        "Buy Price",
                        "Current Price",
                        "Pct Change",
                        "Stop Loss",
                        "Value",
                        "PnL",
                    ]

                    styled = (
                        port_table.style.format(
                            {
                                "Shares": fmt_shares,
                                "Buy Price": fmt_currency,
                                "Current Price": fmt_currency,
                                "Stop Loss": fmt_currency,
                                "Value": fmt_currency,
                                "PnL": fmt_currency,
                                "Pct Change": fmt_percent,
                            }
                        )
                        .set_properties(
                            subset=numeric_display, **{"text-align": "right"}
                        )
                        .applymap(highlight_pct, subset=["Pct Change"])
                        .applymap(color_pnl, subset=["PnL"])
                        .apply(highlight_stop, axis=1)
                        .set_table_styles(
                            [
                                {
                                    "selector": "th",
                                    "props": [
                                        ("font-size", "16px"),
                                        ("text-align", "center"),
                                    ],
                                },
                                {
                                    "selector": "td",
                                    "props": [
                                        ("font-size", "16px"),
                                        ("color", "black"),
                                    ],
                                },
                            ]
                        )
                    )

                    column_config = {
                        "Stop Loss": st.column_config.NumberColumn(
                            "Stop Loss",
                            help="Price at which the stock will be sold to limit loss",
                        ),
                        "Pct Change": st.column_config.NumberColumn(
                            "Pct Change", help="Percentage change since purchase"
                        ),
                        "PnL": st.column_config.NumberColumn(
                            "PnL", help="Profit or loss"
                        ),
                        "Value": st.column_config.NumberColumn(
                            "Value", help="Current market value"
                        ),
                        "Buy Price": st.column_config.NumberColumn(
                            "Buy Price", help="Average price paid per share"
                        ),
                    }
                    st.dataframe(
                        styled,
                        use_container_width=True,
                        column_config=column_config,
                        hide_index=True,
                    )

            show_buy_form()
            if not port_table.empty:
                show_sell_form()

            # --------------------------------------------------------------
            # Section 3: Daily Summary
            # --------------------------------------------------------------
            st.subheader("Daily Summary")
            if st.button("Generate Daily Summary"):
                if not summary_df.empty:
                    st.session_state.daily_summary = build_daily_summary(summary_df)
                    st.session_state.summary_visible = True
                else:
                    st.info("No summary available.")
            if (
                st.session_state.get("summary_visible")
                and st.session_state.get("daily_summary")
            ):
                st.code(st.session_state.daily_summary, language="markdown")
                st.button(
                    "Dismiss Summary", key="dismiss_summary", on_click=dismiss_summary
                )

            # --------------------------------------------------------------
            # Section 4: Error Log
            # --------------------------------------------------------------
            if st.session_state.get("error_log"):
                st.subheader("Error Log")
                for line in st.session_state.error_log:
                    st.text(line)

    with guide_tab:
        st.header("User Guide")
        st.markdown(
            """
            ### Getting Started
            1. **Set a starting cash balance.** When you first open the app the dashboard
               will ask for an initial amount of cash to trade with.
            2. **Maintain a watchlist.** Use the sidebar lookup to search for tickers and
               add them to your personal watchlist.

            ### Buying Stocks
            1. Open the *Log a Buy* form.
            2. Enter the ticker symbol, number of shares, and the price you paid.
            3. Provide a **Stop Loss %**. For example, entering `10` will set a stop price
               10% below your purchase price. The app stores the calculated price for you.

            ### Selling Stocks
            - Once you hold a position it will appear in the *Current Portfolio* table.
              Use the *Log a Sell* form to close or trim a position.

            ### Current Portfolio Table
            - Shows each holding with buy price, current price, stop loss and
              unrealised profit or loss. Refresh prices manually or enable
              auto-refresh for updates every 30 minutes.

            ### Daily Summary
            - Use the *Generate Daily Summary* button to create a markdown snapshot of
              your portfolio and watchlist for easy sharing or journaling.

            ### Tips
            - Add extra funds at any time using the *Add Cash* button.
            - Stop losses are stored as dollar prices even though you input a
              percentage.
            - The app saves data to the local `data/` folder so you can pick up where
              you left off.
            """
        )


if __name__ == "__main__":
    main()
