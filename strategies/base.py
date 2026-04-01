"""Base strategy interface — all strategies implement this."""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np


class Strategy(ABC):
    """Base class for all trading strategies.

    Subclasses must implement `generate_signals()` which returns a DataFrame
    with a 'signal' column: 1 = long, -1 = short, 0 = flat.
    """

    name: str = "BaseStrategy"
    description: str = ""
    default_params: dict = {}

    def __init__(self, **params):
        self.params = {**self.default_params, **params}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from OHLCV data.

        Args:
            df: DataFrame with Open, High, Low, Close, Volume columns

        Returns:
            DataFrame with added indicator columns and a 'signal' column
            signal: 1 (buy/long), -1 (sell/short), 0 (flat/no position)
        """
        ...

    def __repr__(self):
        return f"{self.name}({self.params})"
