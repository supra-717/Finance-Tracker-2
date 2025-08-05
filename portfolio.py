from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import pandas as pd

# ---------------------------------------------------------------------------
# Portfolio schema and helpers
# ---------------------------------------------------------------------------

PORTFOLIO_COLUMNS: List[str] = [
    "ticker",
    "shares",
    "stop_loss",
    "buy_price",
    "cost_basis",
]


@dataclass
class PortfolioRecord:
    """Dataclass representing a single portfolio holding."""

    ticker: str
    shares: float
    stop_loss: float
    buy_price: float
    cost_basis: float = field(init=False)

    def __post_init__(self) -> None:
        self.cost_basis = self.shares * self.buy_price


def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with all expected portfolio columns present."""

    for col in PORTFOLIO_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0 if col != "ticker" else ""
    return df[PORTFOLIO_COLUMNS].copy()
