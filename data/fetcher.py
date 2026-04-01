"""Market data fetcher — supports yfinance (stocks) and ccxt (Binance crypto)."""

import pandas as pd
import yfinance as yf
import ccxt
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_stock(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """Fetch stock OHLCV data via yfinance.

    Args:
        symbol: Ticker symbol (e.g. "AAPL", "SPY")
        start: Start date "YYYY-MM-DD"
        end: End date "YYYY-MM-DD"
        interval: "1d", "1h", "5m", etc.

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    cache_file = DATA_DIR / f"{symbol}_{start}_{end}_{interval}.csv"
    if cache_file.exists():
        df = pd.read_csv(cache_file, index_col="Date", parse_dates=True)
        return df

    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.index.name = "Date"
    df.index = df.index.tz_localize(None)

    df.to_csv(cache_file)
    return df


def fetch_crypto(symbol: str, start: str, end: str, timeframe: str = "1d") -> pd.DataFrame:
    """Fetch crypto OHLCV data from Binance via ccxt.

    Args:
        symbol: Trading pair (e.g. "BTC/USDT")
        start: Start date "YYYY-MM-DD"
        end: End date "YYYY-MM-DD"
        timeframe: "1m", "5m", "15m", "1h", "4h", "1d"

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    safe_symbol = symbol.replace("/", "-")
    cache_file = DATA_DIR / f"{safe_symbol}_{start}_{end}_{timeframe}.csv"
    if cache_file.exists():
        df = pd.read_csv(cache_file, index_col="Date", parse_dates=True)
        return df

    exchange = ccxt.binance({"enableRateLimit": True})
    since = int(datetime.strptime(start, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp() * 1000)

    all_ohlcv = []
    while since < end_ts:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1

    df = pd.DataFrame(all_ohlcv, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Timestamp"], unit="ms")
    df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
    df = df[df.index <= end]

    df.to_csv(cache_file)
    return df


def fetch(symbol: str, start: str, end: str,
          source: str = "auto", timeframe: str = "1d") -> pd.DataFrame:
    """Unified data fetcher — auto-detects source from symbol format.

    Args:
        symbol: "AAPL" for stocks, "BTC/USDT" for crypto
        source: "auto" | "yfinance" | "binance"
        timeframe: candle interval
    """
    if source == "auto":
        source = "binance" if "/" in symbol else "yfinance"

    if source == "yfinance":
        return fetch_stock(symbol, start, end, interval=timeframe)
    elif source == "binance":
        return fetch_crypto(symbol, start, end, timeframe=timeframe)
    else:
        raise ValueError(f"Unknown data source: {source}")
