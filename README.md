# Quant Trading Backtest System

A Python-based quantitative trading backtesting framework that supports both equities (via Interactive Brokers / yFinance) and crypto (via Binance/CCXT). Runs 5 built-in strategies, generates PDF performance reports, and ships with a Flask web UI.

## Features

- **5 Built-in Strategies**
  - Moving Average Crossover (EMA/SMA)
  - MACD Strategy
  - Bollinger Bands
  - RSI Mean Reversion
  - Momentum

- **Data Sources**
  - Equities: Yahoo Finance (`yfinance`)
  - Crypto: Binance via `ccxt`

- **Performance Metrics**
  - Total Return, Sharpe Ratio, Sortino Ratio
  - Max Drawdown, Win Rate, Trade Count
  - Benchmark comparison (default: SPY)

- **Reporting**
  - Auto-generated PDF reports with equity curves and trade analysis
  - Interactive Flask web dashboard with chart rendering

## Installation

```bash
pip install -r requirements.txt
```

> Note: `ta-lib-bin` requires a system-level TA-Lib install on some platforms.

## Usage

### CLI

```bash
# Run all strategies on AAPL (default)
python main.py

# Crypto backtest
python main.py --symbol BTC/USDT

# Custom date range and capital
python main.py --symbol NVDA --start 2022-01-01 --end 2025-12-31 --capital 50000

# Run specific strategies only
python main.py --strategy "MA Crossover" "MACD"

# List all available strategies
python main.py --list

# Skip PDF generation
python main.py --no-pdf
```

### Web UI

```bash
python web/app.py
```

Then open `http://localhost:5000` to use the interactive dashboard.

## Project Structure

```
quant-trading/
├── main.py                  # CLI entry point
├── config.py                # Global configuration
├── requirements.txt
├── data/
│   └── fetcher.py           # IBKR / Binance / yFinance data fetching
├── backtester/
│   ├── engine.py            # Core backtest loop
│   └── metrics.py           # Performance metric calculations
├── strategies/
│   ├── base.py              # Abstract strategy interface
│   ├── ma_crossover.py
│   ├── macd_strategy.py
│   ├── bollinger_bands.py
│   ├── rsi_mean_reversion.py
│   └── momentum.py
├── reports/
│   ├── generator.py         # PDF report builder
│   └── charts.py            # Chart generation (matplotlib / plotly)
└── web/
    ├── app.py               # Flask backend API
    └── static/index.html    # Frontend dashboard
```

## Tech Stack

| Category | Libraries |
|---|---|
| Backtesting | `vectorbt` |
| Data | `yfinance`, `ccxt` |
| Indicators | `ta-lib`, `pandas`, `numpy` |
| Charting | `matplotlib`, `mplfinance`, `plotly` |
| Reports | `fpdf2`, `quantstats` |
| Web | `Flask` |
| ML (optional) | `scikit-learn` |
