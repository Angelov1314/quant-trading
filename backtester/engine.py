"""Backtesting engine — runs strategies on historical data and computes P&L."""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.base import Strategy
from config import BacktestConfig


@dataclass
class BacktestResult:
    """Container for a single backtest run's output."""
    strategy_name: str
    symbol: str
    config: BacktestConfig
    signals_df: pd.DataFrame       # OHLCV + indicators + signals
    trades_df: pd.DataFrame        # individual trades log
    equity_curve: pd.Series        # daily portfolio value
    returns: pd.Series             # daily returns
    benchmark_returns: Optional[pd.Series] = None
    params: dict = field(default_factory=dict)


class BacktestEngine:
    """Vectorized backtesting engine with transaction cost modeling."""

    def __init__(self, config: BacktestConfig):
        self.config = config

    def run(self, strategy: Strategy, data: pd.DataFrame,
            benchmark_data: Optional[pd.DataFrame] = None) -> BacktestResult:
        """Run a backtest for a given strategy on OHLCV data.

        Args:
            strategy: Strategy instance with generate_signals()
            data: OHLCV DataFrame
            benchmark_data: Optional benchmark OHLCV for comparison

        Returns:
            BacktestResult with full equity curve, trades, and metrics
        """
        df = strategy.generate_signals(data)
        df = df.dropna(subset=["signal"])

        # Position changes (where we actually trade)
        df["position"] = df["signal"]
        df["pos_change"] = df["position"].diff().fillna(df["position"])

        # Daily returns from holding position
        df["market_return"] = df["Close"].pct_change()
        df["strategy_return"] = df["position"].shift(1) * df["market_return"]

        # Transaction costs on position changes
        cost = self.config.commission_pct + self.config.slippage_pct
        df["trade_cost"] = df["pos_change"].abs() * cost
        df["strategy_return"] = df["strategy_return"] - df["trade_cost"]
        df["strategy_return"] = df["strategy_return"].fillna(0)

        # Equity curve
        df["equity"] = self.config.initial_capital * (1 + df["strategy_return"]).cumprod()
        equity_curve = df["equity"]

        # Build trades log
        trades_df = self._extract_trades(df)

        # Benchmark returns
        benchmark_returns = None
        if benchmark_data is not None and len(benchmark_data) > 0:
            benchmark_returns = benchmark_data["Close"].pct_change().dropna()
            # Align index
            common_idx = equity_curve.index.intersection(benchmark_returns.index)
            if len(common_idx) > 0:
                benchmark_returns = benchmark_returns.loc[common_idx]

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=self.config.symbol,
            config=self.config,
            signals_df=df,
            trades_df=trades_df,
            equity_curve=equity_curve,
            returns=df["strategy_return"],
            benchmark_returns=benchmark_returns,
            params=strategy.params,
        )

    def _extract_trades(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract individual trades from position changes."""
        trades = []
        position = 0
        entry_price = 0.0
        entry_date = None

        for date, row in df.iterrows():
            new_pos = row["position"]
            if new_pos != position:
                # Close existing position
                if position != 0 and entry_date is not None:
                    pnl_pct = (row["Close"] / entry_price - 1) * position
                    trades.append({
                        "entry_date": entry_date,
                        "exit_date": date,
                        "side": "LONG" if position > 0 else "SHORT",
                        "entry_price": entry_price,
                        "exit_price": row["Close"],
                        "pnl_pct": pnl_pct,
                        "duration_days": (date - entry_date).days,
                    })
                # Open new position
                if new_pos != 0:
                    entry_price = row["Close"]
                    entry_date = date
                else:
                    entry_date = None
                position = new_pos

        return pd.DataFrame(trades) if trades else pd.DataFrame(
            columns=["entry_date", "exit_date", "side", "entry_price",
                     "exit_price", "pnl_pct", "duration_days"]
        )
