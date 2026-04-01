"""Chart generation for backtest reports — saves to PNG for PDF embedding."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import numpy as np
from pathlib import Path


STYLE = {
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor": "#16213e",
    "axes.edgecolor": "#e94560",
    "axes.labelcolor": "#eee",
    "text.color": "#eee",
    "xtick.color": "#aaa",
    "ytick.color": "#aaa",
    "grid.color": "#2a2a4a",
    "grid.alpha": 0.5,
}


def _apply_style():
    plt.rcParams.update(STYLE)
    plt.rcParams["font.size"] = 10


def save_equity_curve(equity: pd.Series, benchmark_equity: pd.Series = None,
                      title: str = "Equity Curve", path: str = "equity.png") -> str:
    """Plot equity curve with optional benchmark overlay."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 4.5))

    ax.plot(equity.index, equity.values, color="#00d2ff", linewidth=1.5, label="Strategy")
    if benchmark_equity is not None and len(benchmark_equity) > 0:
        ax.plot(benchmark_equity.index, benchmark_equity.values,
                color="#ff6b6b", linewidth=1, alpha=0.7, label="Benchmark")
        ax.legend(loc="upper left", framealpha=0.3)

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel("Portfolio Value ($)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def save_drawdown_chart(equity: pd.Series, path: str = "drawdown.png") -> str:
    """Plot drawdown percentage over time."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 3))

    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax * 100

    ax.fill_between(drawdown.index, drawdown.values, 0,
                    color="#e94560", alpha=0.6)
    ax.plot(drawdown.index, drawdown.values, color="#e94560", linewidth=0.8)

    ax.set_title("Drawdown", fontsize=12, fontweight="bold")
    ax.set_ylabel("Drawdown %")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def save_monthly_returns_heatmap(returns: pd.Series, path: str = "monthly.png") -> str:
    """Monthly returns heatmap — rows=year, columns=month."""
    _apply_style()

    monthly = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    monthly_df = pd.DataFrame({
        "year": monthly.index.year,
        "month": monthly.index.month,
        "return": monthly.values,
    })
    pivot = monthly_df.pivot_table(index="year", columns="month", values="return", aggfunc="first")
    pivot.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][:len(pivot.columns)]

    fig, ax = plt.subplots(figsize=(10, max(3, len(pivot) * 0.6)))
    im = ax.imshow(pivot.values * 100, cmap="RdYlGn", aspect="auto",
                   vmin=-10, vmax=10)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                color = "#000" if abs(val) < 0.05 else "#fff"
                ax.text(j, i, f"{val*100:.1f}%", ha="center", va="center",
                        fontsize=8, color=color)

    ax.set_title("Monthly Returns (%)", fontsize=12, fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.8, label="%")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def save_trade_distribution(trades_df: pd.DataFrame, path: str = "trades.png") -> str:
    """Histogram of trade P&L distribution."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 3.5))

    if len(trades_df) == 0:
        ax.text(0.5, 0.5, "No trades", ha="center", va="center", fontsize=14)
    else:
        pnl = trades_df["pnl_pct"] * 100
        colors = ["#00d2ff" if x > 0 else "#e94560" for x in pnl]
        ax.bar(range(len(pnl)), pnl, color=colors, alpha=0.8)
        ax.axhline(0, color="#aaa", linewidth=0.5)
        ax.set_xlabel("Trade #")
        ax.set_ylabel("P&L %")

    ax.set_title("Trade P&L Distribution", fontsize=12, fontweight="bold")
    ax.grid(True, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def save_strategy_comparison(results_list: list, path: str = "comparison.png") -> str:
    """Compare equity curves of multiple strategies on the same chart."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 5))

    colors = ["#00d2ff", "#e94560", "#ffd93d", "#6bcb77", "#a855f7",
              "#ff6b6b", "#4ecdc4", "#f7dc6f"]

    for i, result in enumerate(results_list):
        color = colors[i % len(colors)]
        normalized = result.equity_curve / result.equity_curve.iloc[0] * 100
        ax.plot(normalized.index, normalized.values, color=color,
                linewidth=1.5, label=result.strategy_name)

    ax.set_title("Strategy Comparison (Normalized to 100)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Portfolio Value (base=100)")
    ax.legend(loc="upper left", framealpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
