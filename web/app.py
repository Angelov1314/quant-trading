"""Flask web app — API backend for the quant trading dashboard."""

import sys
import json
import io
import base64
import traceback
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, send_file

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BacktestConfig, STOCK_SYMBOLS, BINANCE_SYMBOLS, REPORTS_DIR
from data.fetcher import fetch
from backtester.engine import BacktestEngine, BacktestResult
from backtester.metrics import PerformanceMetrics
from strategies import ALL_STRATEGIES
from reports.generator import ReportGenerator
from reports import charts

import tempfile
import matplotlib
matplotlib.use("Agg")

app = Flask(__name__, static_folder="static")

# In-memory cache for latest results (per session, simplified)
_latest_results: list[BacktestResult] = []
_latest_metrics: list[dict] = []


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/strategies")
def get_strategies():
    """Return list of available strategies and their default params."""
    strats = []
    for cls in ALL_STRATEGIES:
        s = cls()
        strats.append({
            "name": s.name,
            "description": s.description,
            "params": s.default_params,
        })
    return jsonify(strats)


@app.route("/api/symbols")
def get_symbols():
    return jsonify({
        "stocks": STOCK_SYMBOLS,
        "crypto": BINANCE_SYMBOLS,
    })


@app.route("/api/backtest", methods=["POST"])
def run_backtest():
    """Run backtest and return results as JSON with base64-encoded chart images."""
    global _latest_results, _latest_metrics

    try:
        body = request.json
        symbol = body.get("symbol", "AAPL")
        start = body.get("start", "2023-01-01")
        end = body.get("end", "2025-12-31")
        capital = float(body.get("capital", 100000))
        commission = float(body.get("commission", 0.001))
        strategy_names = body.get("strategies", [])
        benchmark = body.get("benchmark", "SPY")

        config = BacktestConfig(
            symbol=symbol, start_date=start, end_date=end,
            initial_capital=capital, commission_pct=commission,
            benchmark=benchmark,
        )

        # Fetch data
        data = fetch(symbol, start, end)
        benchmark_data = None
        if "/" not in symbol:
            try:
                benchmark_data = fetch(benchmark, start, end)
            except Exception:
                pass

        # Select strategies
        if strategy_names:
            selected = [s for s in ALL_STRATEGIES if s().name in strategy_names]
        else:
            selected = ALL_STRATEGIES

        if not selected:
            return jsonify({"error": "No valid strategies selected"}), 400

        # Run backtests
        engine = BacktestEngine(config)
        results = []
        metrics_list = []

        for cls in selected:
            strategy = cls()
            result = engine.run(strategy, data, benchmark_data)
            m = PerformanceMetrics.from_backtest(
                result.equity_curve, result.returns,
                result.trades_df, result.benchmark_returns,
            )
            results.append(result)
            metrics_list.append(m.to_dict())

        _latest_results = results
        _latest_metrics = metrics_list

        # Generate chart images as base64
        chart_images = {}
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Strategy comparison
            if len(results) > 1:
                path = charts.save_strategy_comparison(results, str(tmp / "comp.png"))
                chart_images["comparison"] = _img_to_base64(path)

            # Per-strategy charts
            for i, result in enumerate(results):
                name = result.strategy_name

                bench_eq = None
                if result.benchmark_returns is not None:
                    common = result.equity_curve.index.intersection(result.benchmark_returns.index)
                    if len(common) > 0:
                        bench_eq = config.initial_capital * (
                            1 + result.benchmark_returns.loc[common]
                        ).cumprod()

                eq_path = charts.save_equity_curve(
                    result.equity_curve, bench_eq,
                    title=f"{name} - {symbol}",
                    path=str(tmp / f"eq_{i}.png"),
                )
                dd_path = charts.save_drawdown_chart(
                    result.equity_curve, path=str(tmp / f"dd_{i}.png"),
                )
                mr_path = charts.save_monthly_returns_heatmap(
                    result.returns, path=str(tmp / f"mr_{i}.png"),
                )
                td_path = charts.save_trade_distribution(
                    result.trades_df, path=str(tmp / f"td_{i}.png"),
                )

                chart_images[f"{name}_equity"] = _img_to_base64(eq_path)
                chart_images[f"{name}_drawdown"] = _img_to_base64(dd_path)
                chart_images[f"{name}_monthly"] = _img_to_base64(mr_path)
                chart_images[f"{name}_trades"] = _img_to_base64(td_path)

        # Build response
        response_data = []
        for result, metrics in zip(results, metrics_list):
            trades = []
            if len(result.trades_df) > 0:
                for _, t in result.trades_df.head(50).iterrows():
                    trades.append({
                        "entry_date": str(t["entry_date"])[:10],
                        "exit_date": str(t["exit_date"])[:10],
                        "side": t["side"],
                        "entry_price": round(t["entry_price"], 2),
                        "exit_price": round(t["exit_price"], 2),
                        "pnl_pct": round(t["pnl_pct"] * 100, 2),
                        "duration_days": int(t["duration_days"]),
                    })

            response_data.append({
                "strategy": result.strategy_name,
                "params": result.params,
                "metrics": metrics,
                "trades": trades,
            })

        return jsonify({
            "symbol": symbol,
            "period": f"{start} to {end}",
            "bars": len(data),
            "results": response_data,
            "charts": chart_images,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/download-pdf", methods=["POST"])
def download_pdf():
    """Generate and download PDF report from the latest backtest results."""
    global _latest_results
    if not _latest_results:
        return jsonify({"error": "No backtest results. Run a backtest first."}), 400

    try:
        gen = ReportGenerator()
        pdf_path = gen.generate(_latest_results)
        return send_file(pdf_path, as_attachment=True,
                         download_name=Path(pdf_path).name,
                         mimetype="application/pdf")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


if __name__ == "__main__":
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    app.run(debug=True, port=5555)
