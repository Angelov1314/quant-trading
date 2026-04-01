"""Moving Average Crossover — classic trend-following strategy."""

import pandas as pd
from .base import Strategy


class MACrossover(Strategy):
    name = "MA Crossover"
    description = "Buy when fast MA crosses above slow MA, sell on cross below."
    default_params = {"fast_period": 10, "slow_period": 50, "ma_type": "EMA"}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        ma_type = self.params["ma_type"]

        if ma_type == "EMA":
            df["fast_ma"] = df["Close"].ewm(span=fast, adjust=False).mean()
            df["slow_ma"] = df["Close"].ewm(span=slow, adjust=False).mean()
        else:
            df["fast_ma"] = df["Close"].rolling(fast).mean()
            df["slow_ma"] = df["Close"].rolling(slow).mean()

        df["signal"] = 0
        df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1
        df.loc[df["fast_ma"] < df["slow_ma"], "signal"] = -1

        return df
