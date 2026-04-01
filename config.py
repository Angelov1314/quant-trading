"""Global configuration for the quant trading system."""

from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "cache"
REPORTS_DIR = BASE_DIR / "reports" / "output"


@dataclass
class BacktestConfig:
    """Configuration for a single backtest run."""
    symbol: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    initial_capital: float = 100_000.0
    commission_pct: float = 0.001  # 0.1%
    slippage_pct: float = 0.0005  # 0.05%
    data_source: str = "yfinance"  # "yfinance" | "binance"
    timeframe: str = "1d"  # 1m, 5m, 15m, 1h, 4h, 1d
    benchmark: str = "SPY"  # benchmark symbol for comparison


@dataclass
class StrategyParams:
    """Base strategy parameters — each strategy extends this."""
    name: str = ""
    params: dict = field(default_factory=dict)


# Default data sources
BINANCE_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
    "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOGE/USDT",
]

STOCK_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "SPY", "QQQ", "IWM",
]
