from datetime import datetime
from pathlib import Path

from portfolio import PORTFOLIO_COLUMNS

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

PORTFOLIO_CSV = DATA_DIR / "chatgpt_portfolio_update.csv"
TRADE_LOG_CSV = DATA_DIR / "chatgpt_trade_log.csv"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"

COL_TICKER, COL_SHARES, COL_STOP, COL_PRICE, COL_COST = PORTFOLIO_COLUMNS

TODAY = datetime.today().strftime("%Y-%m-%d")
