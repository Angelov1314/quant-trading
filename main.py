#!/usr/bin/env python3
"""Quant Trading Backtest System — CLI entry point.

Usage:
    python main.py                          # Run all strategies on AAPL (default)
    python main.py --symbol BTC/USDT        # Crypto from Binance
    python main.py --symbol NVDA --start 2022-01-01 --end 2025-12-31
    python main.py --strategy "MA Crossover" "MACD"   # Specific strategies only
    python main.py --list                   # List all available strategies
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import BacktestConfig
from data.fetcher import fetch
from backtester.engine import BacktestEngine, BacktestResult
from backtester.metrics import PerformanceMetrics
from strategies import ALL_STRATEGIES
from reports.generator import ReportGenerator


def parse_args():
    p = argparse.ArgumentParser(description="Quant Trading Backtest System")
    p.add_argument("--symbol", default="AAPL", help="Symbol to backtest (e.g. AAPL, BTC/USDT)")
    p.add_argument("--start", default="2022-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", default="2025-12-31", help="End date YYYY-MM-DD")
    p.add_argument("--capital", type=float, default=100_000, help="Initial capital ($)")
    p.add_argument("--commission", type=float, default=0.001, help="Commission (0.001 = 0.1%%)")
    p.add_argument("--timeframe", default="1d", help="Candle timeframe (1d, 1h, etc.)")
    p.add_argument("--benchmark", default="SPY", help="Benchmark symbol")
    p.add_argument("--strategy", nargs="*", help="Strategy names to run (default: all)")
    p.add_argument("--list", action="store_true", help="List available strategies")
    p.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")
    return p.parse_args()


def main():
    args = parse_args()

    if args.list:
        print("\nAvailable strategies:")
        for s in ALL_STRATEGIES:
            inst = s()
            print(f"  - {inst.name}: {inst.description}")
            print(f"    Default params: {inst.default_params}")
        return

    # Config
    config = BacktestConfig(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        commission_pct=args.commission,
        timeframe=args.timeframe,
        benchmark=args.benchmark,
    )

    print(f"\n{'='*60}")
    print(f"  Quant Backtest: {config.symbol}")
    print(f"  Period: {config.start_date} → {config.end_date}")
    print(f"  Capital: ${config.initial_capital:,.0f}")
    print(f"{'='*60}\n")

    # Fetch data
    print(f"[1/4] Fetching {config.symbol} data...")
    data = fetch(config.symbol, config.start_date, config.end_date,
                 timeframe=config.timeframe)
    print(f"  → {len(data)} bars loaded ({data.index[0].date()} to {data.index[-1].date()})")

    # Fetch benchmark
    benchmark_data = None
    if "/" not in config.symbol:  # stocks only
        print(f"  Fetching benchmark ({config.benchmark})...")
        try:
            benchmark_data = fetch(config.benchmark, config.start_date, config.end_date)
        except Exception as e:
            print(f"  ⚠ Benchmark fetch failed: {e}")

    # Select strategies
    if args.strategy:
        selected = [s for s in ALL_STRATEGIES
                    if s().name in args.strategy]
        if not selected:
            print(f"Error: No matching strategies for {args.strategy}")
            print(f"Available: {[s().name for s in ALL_STRATEGIES]}")
            return
    else:
        selected = ALL_STRATEGIES

    # Run backtests
    print(f"\n[2/4] Running {len(selected)} strategies...")
    engine = BacktestEngine(config)
    results: list[BacktestResult] = []

    for strat_cls in selected:
        strategy = strat_cls()
        print(f"  → {strategy.name}...", end=" ")
        result = engine.run(strategy, data, benchmark_data)
        metrics = PerformanceMetrics.from_backtest(
            result.equity_curve, result.returns,
            result.trades_df, result.benchmark_returns,
        )
        results.append(result)
        print(f"Return: {metrics.total_return:+.1%} | "
              f"Sharpe: {metrics.sharpe_ratio:.2f} | "
              f"MaxDD: {metrics.max_drawdown:.1%} | "
              f"Trades: {metrics.total_trades}")

    # Summary comparison
    print(f"\n[3/4] Strategy Comparison:")
    print(f"  {'Strategy':<20} {'Return':>10} {'Sharpe':>8} {'Sortino':>8} {'MaxDD':>8} {'WinRate':>8}")
    print(f"  {'-'*62}")
    for r in results:
        m = PerformanceMetrics.from_backtest(
            r.equity_curve, r.returns, r.trades_df, r.benchmark_returns
        )
        print(f"  {r.strategy_name:<20} {m.total_return:>+9.1%} {m.sharpe_ratio:>8.2f} "
              f"{m.sortino_ratio:>8.2f} {m.max_drawdown:>8.1%} {m.win_rate:>7.0%}")

    # Generate PDF
    if not args.no_pdf:
        print(f"\n[4/4] Generating PDF report...")
        gen = ReportGenerator()
        pdf_path = gen.generate(results)
        print(f"  → Report saved: {pdf_path}")
    else:
        print(f"\n[4/4] PDF generation skipped (--no-pdf)")

    print(f"\n{'='*60}")
    print(f"  Done!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
