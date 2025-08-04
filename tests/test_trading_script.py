import pandas as pd
from types import SimpleNamespace
import trading_script


def test_set_data_dir_updates_paths(tmp_path):
    new_dir = tmp_path / "data"
    trading_script.set_data_dir(new_dir)
    assert trading_script.DATA_DIR == new_dir
    assert trading_script.PORTFOLIO_CSV == new_dir / "chatgpt_portfolio_update.csv"
    assert trading_script.TRADE_LOG_CSV == new_dir / "chatgpt_trade_log.csv"
    assert new_dir.exists()


def test_process_portfolio_input_normalization(monkeypatch, tmp_path):
    trading_script.set_data_dir(tmp_path)
    trading_script.day = 0
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "")

    class DummyTicker:
        def __init__(self, ticker):
            pass

        def history(self, period):
            return pd.DataFrame({"Low": [10.0], "Close": [10.0]})

    monkeypatch.setattr(trading_script.yf, "Ticker", DummyTicker)

    portfolio_variants = [
        {
            "ticker": ["ABC"],
            "shares": [1],
            "stop_loss": [4.0],
            "buy_price": [5.0],
        },
        [
            {
                "ticker": "ABC",
                "shares": 1,
                "stop_loss": 4.0,
                "buy_price": 5.0,
            }
        ],
    ]

    expected = pd.DataFrame(
        {
            "ticker": ["ABC"],
            "shares": [1],
            "stop_loss": [4.0],
            "buy_price": [5.0],
        }
    )
    for portfolio in portfolio_variants:
        portfolio_df, cash = trading_script.process_portfolio(portfolio, 1000.0)
        pd.testing.assert_frame_equal(
            portfolio_df.reset_index(drop=True), expected
        )
        assert cash == 1000.0


def test_load_latest_portfolio_state(tmp_path):
    data = pd.DataFrame(
        [
            {
                "Date": "2023-01-01",
                "Ticker": "ABC",
                "Shares": 10,
                "Cost Basis": 5,
                "Stop Loss": 3,
                "Current Price": 5,
                "Total Value": 50,
                "PnL": 0,
                "Action": "HOLD",
                "Cash Balance": "",
                "Total Equity": "",
            },
            {
                "Date": "2023-01-01",
                "Ticker": "TOTAL",
                "Shares": "",
                "Cost Basis": "",
                "Stop Loss": "",
                "Current Price": "",
                "Total Value": 50,
                "PnL": 0,
                "Action": "",
                "Cash Balance": 1000,
                "Total Equity": 1050,
            },
            {
                "Date": "2023-01-02",
                "Ticker": "ABC",
                "Shares": 10,
                "Cost Basis": 5,
                "Stop Loss": 3,
                "Current Price": 5,
                "Total Value": 50,
                "PnL": 0,
                "Action": "HOLD",
                "Cash Balance": "",
                "Total Equity": "",
            },
            {
                "Date": "2023-01-02",
                "Ticker": "TOTAL",
                "Shares": "",
                "Cost Basis": "",
                "Stop Loss": "",
                "Current Price": "",
                "Total Value": 50,
                "PnL": 0,
                "Action": "",
                "Cash Balance": 1005,
                "Total Equity": 1055,
            },
        ]
    )
    csv_path = tmp_path / "portfolio.csv"
    data.to_csv(csv_path, index=False)

    holdings, cash = trading_script.load_latest_portfolio_state(str(csv_path))

    assert holdings == [
        {
            "Ticker": "ABC",
            "Stop Loss": 3,
            "buy_price": 5,
            "shares": 10,
            "cost_basis": 50,
        }
    ]
    assert cash == 1005.0
