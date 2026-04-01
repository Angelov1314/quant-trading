"""RSI Mean Reversion — buy oversold, sell overbought."""

import pandas as pd
import numpy as np
from .base import Strategy


class RSIMeanReversion(Strategy):
    name = "RSI Mean Reversion"
    description = "Buy when RSI < oversold, sell when RSI > overbought."
    default_params = {"rsi_period": 14, "oversold": 30, "overbought": 70}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        period = self.params["rsi_period"]

        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        df["signal"] = 0
        df.loc[df["rsi"] < self.params["oversold"], "signal"] = 1
        df.loc[df["rsi"] > self.params["overbought"], "signal"] = -1

        return df
