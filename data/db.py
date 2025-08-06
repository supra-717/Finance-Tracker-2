import sqlite3

from config import DB_FILE

SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio (
    ticker TEXT PRIMARY KEY,
    shares REAL,
    stop_loss REAL,
    buy_price REAL,
    cost_basis REAL
);
CREATE TABLE IF NOT EXISTS cash (
    id INTEGER PRIMARY KEY CHECK (id = 0),
    balance REAL
);
CREATE TABLE IF NOT EXISTS trade_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    ticker TEXT,
    shares_bought REAL,
    buy_price REAL,
    cost_basis REAL,
    pnl REAL,
    reason TEXT,
    shares_sold REAL,
    sell_price REAL
);
CREATE TABLE IF NOT EXISTS portfolio_history (
    date TEXT,
    ticker TEXT,
    shares REAL,
    cost_basis REAL,
    stop_loss REAL,
    current_price REAL,
    total_value REAL,
    pnl REAL,
    action TEXT,
    cash_balance REAL,
    total_equity REAL
);
"""


def get_connection() -> sqlite3.Connection:
    """Return a SQLite3 connection to the trading database."""
    conn = sqlite3.connect(DB_FILE)
    return conn


def init_db() -> None:
    """Initialise the database with required tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
