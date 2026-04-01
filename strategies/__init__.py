from .base import Strategy
from .ma_crossover import MACrossover
from .rsi_mean_reversion import RSIMeanReversion
from .bollinger_bands import BollingerBands
from .momentum import MomentumStrategy
from .macd_strategy import MACDStrategy

ALL_STRATEGIES = [
    MACrossover,
    RSIMeanReversion,
    BollingerBands,
    MomentumStrategy,
    MACDStrategy,
]
