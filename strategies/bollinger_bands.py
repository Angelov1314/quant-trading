"""Bollinger Bands — mean reversion with volatility bands."""

import pandas as pd
from .base import Strategy


class BollingerBands(Strategy):
    name = "Bollinger Bands"
    description = "Buy at lower band, sell at upper band. Mean reversion with volatility."
    default_params = {"period": 20, "std_dev": 2.0}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        period = self.params["period"]
        std = self.params["std_dev"]

        df["bb_mid"] = df["Close"].rolling(period).mean()
        df["bb_std"] = df["Close"].rolling(period).std()
        df["bb_upper"] = df["bb_mid"] + std * df["bb_std"]
        df["bb_lower"] = df["bb_mid"] - std * df["bb_std"]

        df["signal"] = 0
        df.loc[df["Close"] < df["bb_lower"], "signal"] = 1   # oversold
        df.loc[df["Close"] > df["bb_upper"], "signal"] = -1  # overbought

        return df
