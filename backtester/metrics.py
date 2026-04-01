"""Performance metrics — Sharpe, Sortino, Max Drawdown, VaR, etc."""

import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Computed performance metrics for a backtest."""
    total_return: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration_days: int
    volatility: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_pnl: float
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    avg_holding_days: float
    var_95: float       # Value at Risk 95%
    cvar_95: float      # Conditional VaR 95%
    alpha: float        # vs benchmark
    beta: float         # vs benchmark

    def to_dict(self) -> dict:
        return {k: round(v, 4) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}

    @classmethod
    def from_backtest(cls, equity: pd.Series, returns: pd.Series,
                      trades_df: pd.DataFrame,
                      benchmark_returns: pd.Series = None,
                      risk_free_rate: float = 0.04,
                      trading_days: int = 252) -> "PerformanceMetrics":
        """Compute all metrics from backtest results."""
        # Basic returns
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        n_years = len(returns) / trading_days
        cagr = (1 + total_return) ** (1 / max(n_years, 0.01)) - 1

        # Risk metrics
        daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
        excess = returns - daily_rf
        vol = returns.std() * np.sqrt(trading_days)

        sharpe = (excess.mean() / returns.std() * np.sqrt(trading_days)
                  if returns.std() > 0 else 0)

        downside = returns[returns < 0].std()
        sortino = (excess.mean() / downside * np.sqrt(trading_days)
                   if downside > 0 else 0)

        # Drawdown
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_dd = drawdown.min()
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0

        # Max drawdown duration
        dd_duration = 0
        max_dd_dur = 0
        for dd_val in drawdown:
            if dd_val < 0:
                dd_duration += 1
                max_dd_dur = max(max_dd_dur, dd_duration)
            else:
                dd_duration = 0

        # VaR / CVaR
        var_95 = returns.quantile(0.05)
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95

        # Trade stats
        n_trades = len(trades_df)
        if n_trades > 0:
            wins = trades_df[trades_df["pnl_pct"] > 0]
            losses = trades_df[trades_df["pnl_pct"] <= 0]
            win_rate = len(wins) / n_trades
            avg_trade = trades_df["pnl_pct"].mean()
            avg_win = wins["pnl_pct"].mean() if len(wins) > 0 else 0
            avg_loss = losses["pnl_pct"].mean() if len(losses) > 0 else 0
            gross_profit = wins["pnl_pct"].sum() if len(wins) > 0 else 0
            gross_loss = abs(losses["pnl_pct"].sum()) if len(losses) > 0 else 1
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
            best = trades_df["pnl_pct"].max()
            worst = trades_df["pnl_pct"].min()
            avg_hold = trades_df["duration_days"].mean()
        else:
            win_rate = avg_trade = avg_win = avg_loss = 0
            profit_factor = best = worst = avg_hold = 0

        # Alpha / Beta vs benchmark
        alpha, beta = 0.0, 0.0
        if benchmark_returns is not None and len(benchmark_returns) > 1:
            common = returns.index.intersection(benchmark_returns.index)
            if len(common) > 10:
                r = returns.loc[common]
                b = benchmark_returns.loc[common]
                cov = np.cov(r, b)
                beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0
                alpha = (r.mean() - daily_rf - beta * (b.mean() - daily_rf)) * trading_days

        return cls(
            total_return=total_return,
            cagr=cagr,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration_days=max_dd_dur,
            volatility=vol,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=n_trades,
            avg_trade_pnl=avg_trade,
            avg_win=avg_win,
            avg_loss=avg_loss,
            best_trade=best,
            worst_trade=worst,
            avg_holding_days=avg_hold,
            var_95=var_95,
            cvar_95=cvar_95,
            alpha=alpha,
            beta=beta,
        )
