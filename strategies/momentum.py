"""Momentum Strategy — ride trends using rate of change + volume confirmation."""

import pandas as pd
from .base import Strategy


class MomentumStrategy(Strategy):
    name = "Momentum"
    description = "Buy on positive momentum with volume confirmation, sell on reversal."
    default_params = {"roc_period": 12, "vol_ma_period": 20, "vol_threshold": 1.2}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        roc_p = self.params["roc_period"]
        vol_ma = self.params["vol_ma_period"]
        vol_thresh = self.params["vol_threshold"]

        # Rate of change
        df["roc"] = df["Close"].pct_change(roc_p) * 100

        # Volume confirmation
        df["vol_ma"] = df["Volume"].rolling(vol_ma).mean()
        df["vol_ratio"] = df["Volume"] / df["vol_ma"]

        df["signal"] = 0
        # Long: positive momentum + above-average volume
        df.loc[(df["roc"] > 0) & (df["vol_ratio"] > vol_thresh), "signal"] = 1
        # Short: negative momentum + above-average volume
        df.loc[(df["roc"] < 0) & (df["vol_ratio"] > vol_thresh), "signal"] = -1

        return df
