from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from portfolio import ensure_schema, PORTFOLIO_COLUMNS


def test_ensure_schema_adds_missing_columns():
    df = pd.DataFrame({"ticker": ["ABC"], "shares": [10]})
    result = ensure_schema(df)
    assert list(result.columns) == PORTFOLIO_COLUMNS
    # Missing numeric columns should default to 0
    assert result.loc[0, "stop_loss"] == 0
