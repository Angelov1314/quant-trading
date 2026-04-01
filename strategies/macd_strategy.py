"""MACD Strategy — trend following with MACD crossover and histogram."""

import pandas as pd
from .base import Strategy


class MACDStrategy(Strategy):
    name = "MACD"
    description = "Buy on MACD line crossing above signal line, sell on cross below."
    default_params = {"fast": 12, "slow": 26, "signal_period": 9}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        fast = self.params["fast"]
        slow = self.params["slow"]
        sig_p = self.params["signal_period"]

        df["ema_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
        df["ema_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
        df["macd_line"] = df["ema_fast"] - df["ema_slow"]
        df["macd_signal"] = df["macd_line"].ewm(span=sig_p, adjust=False).mean()
        df["macd_hist"] = df["macd_line"] - df["macd_signal"]

        df["signal"] = 0
        df.loc[df["macd_line"] > df["macd_signal"], "signal"] = 1
        df.loc[df["macd_line"] < df["macd_signal"], "signal"] = -1

        return df
