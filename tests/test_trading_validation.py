import pandas as pd

from config import COL_TICKER, COL_SHARES, COL_STOP, COL_PRICE, COL_COST
from services import trading


def _empty_portfolio():
    return pd.DataFrame(columns=[COL_TICKER, COL_SHARES, COL_STOP, COL_PRICE, COL_COST])


def test_manual_buy_rejects_non_positive_values():
    df = _empty_portfolio()
    ok, msg, *_ = trading.manual_buy("ABC", 0, 10, 0, df, 1000)
    assert not ok
    assert "positive" in msg
    ok, msg, *_ = trading.manual_buy("ABC", 1, 0, 0, df, 1000)
    assert not ok
    assert "positive" in msg


def test_manual_sell_rejects_non_positive_values():
    df = pd.DataFrame(
        [{COL_TICKER: "ABC", COL_SHARES: 10, COL_STOP: 0, COL_PRICE: 5, COL_COST: 50}]
    )
    ok, msg, *_ = trading.manual_sell("ABC", 0, 10, df, 0)
    assert not ok
    assert "positive" in msg
    ok, msg, *_ = trading.manual_sell("ABC", 1, 0, df, 0)
    assert not ok
    assert "positive" in msg
