"""PDF Report Generator — produces a professional backtest report."""

import tempfile
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtester.engine import BacktestResult
from backtester.metrics import PerformanceMetrics
from reports import charts
from config import REPORTS_DIR


class ReportPDF(FPDF):
    """Custom PDF with header/footer branding."""

    def __init__(self, title: str):
        super().__init__()
        self.report_title = title

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, self.report_title, align="L")
        self.cell(0, 8, datetime.now().strftime("%Y-%m-%d %H:%M"),
                  align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


class ReportGenerator:
    """Generate PDF backtest reports with charts and metrics."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, results: list[BacktestResult],
                 filename: str = None) -> str:
        """Generate a full PDF report for one or more backtest results.

        Args:
            results: List of BacktestResult objects
            filename: Output filename (auto-generated if None)

        Returns:
            Path to the generated PDF file
        """
        if not results:
            raise ValueError("No backtest results to report")

        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            symbols = "_".join(set(r.symbol for r in results))
            filename = f"backtest_{symbols}_{ts}.pdf"

        pdf = ReportPDF(f"Backtest Report - {results[0].symbol}")
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # --- Page 1: Summary ---
            pdf.add_page()
            self._add_title(pdf, "Backtest Report")
            self._add_summary_table(pdf, results)

            # --- Strategy Comparison Chart (if multiple strategies) ---
            if len(results) > 1:
                chart_path = charts.save_strategy_comparison(results, str(tmp / "comparison.png"))
                pdf.ln(6)
                pdf.image(chart_path, x=10, w=190)

            # --- Per-Strategy Detail Pages ---
            for i, result in enumerate(results):
                metrics = PerformanceMetrics.from_backtest(
                    equity=result.equity_curve,
                    returns=result.returns,
                    trades_df=result.trades_df,
                    benchmark_returns=result.benchmark_returns,
                )

                pdf.add_page()
                self._add_title(pdf, f"Strategy: {result.strategy_name}")
                self._add_params_box(pdf, result)
                self._add_metrics_table(pdf, metrics)

                # Equity curve
                bench_eq = None
                if result.benchmark_returns is not None:
                    common = result.equity_curve.index.intersection(result.benchmark_returns.index)
                    if len(common) > 0:
                        bench_eq = result.config.initial_capital * (
                            1 + result.benchmark_returns.loc[common]
                        ).cumprod()

                eq_path = charts.save_equity_curve(
                    result.equity_curve, bench_eq,
                    title=f"{result.strategy_name} - {result.symbol}",
                    path=str(tmp / f"equity_{i}.png"),
                )
                pdf.ln(4)
                pdf.image(eq_path, x=10, w=190)

                # Drawdown
                dd_path = charts.save_drawdown_chart(
                    result.equity_curve, path=str(tmp / f"dd_{i}.png"),
                )
                pdf.image(dd_path, x=10, w=190)

                # Monthly returns heatmap
                pdf.add_page()
                self._add_title(pdf, f"{result.strategy_name} - Monthly Returns")
                mr_path = charts.save_monthly_returns_heatmap(
                    result.returns, path=str(tmp / f"monthly_{i}.png"),
                )
                pdf.image(mr_path, x=10, w=190)

                # Trade distribution
                td_path = charts.save_trade_distribution(
                    result.trades_df, path=str(tmp / f"trades_{i}.png"),
                )
                pdf.ln(4)
                pdf.image(td_path, x=15, w=170)

                # Trades table (top 20)
                if len(result.trades_df) > 0:
                    pdf.add_page()
                    self._add_title(pdf, f"{result.strategy_name} - Trade Log (Top 20)")
                    self._add_trades_table(pdf, result.trades_df.head(20))

            # Save
            output_path = self.output_dir / filename
            pdf.output(str(output_path))

        return str(output_path)

    def _add_title(self, pdf: FPDF, text: str):
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(30, 30, 60)
        pdf.cell(0, 12, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def _add_summary_table(self, pdf: FPDF, results: list[BacktestResult]):
        """Overview table comparing all strategies."""
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 240, 245)

        headers = ["Strategy", "Symbol", "Period", "Total Return", "Sharpe", "Max DD", "Trades"]
        col_w = [35, 22, 35, 28, 20, 22, 18]

        for h, w in zip(headers, col_w):
            pdf.cell(w, 7, h, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for r in results:
            m = PerformanceMetrics.from_backtest(
                r.equity_curve, r.returns, r.trades_df, r.benchmark_returns
            )
            period = f"{r.config.start_date} ~ {r.config.end_date}"
            row = [
                r.strategy_name,
                r.symbol,
                period,
                f"{m.total_return:.1%}",
                f"{m.sharpe_ratio:.2f}",
                f"{m.max_drawdown:.1%}",
                str(m.total_trades),
            ]
            for val, w in zip(row, col_w):
                pdf.cell(w, 6, val, border=1, align="C")
            pdf.ln()

    def _add_params_box(self, pdf: FPDF, result: BacktestResult):
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(80, 80, 80)
        params_str = " | ".join(f"{k}={v}" for k, v in result.params.items())
        config_str = (f"Capital: ${result.config.initial_capital:,.0f} | "
                      f"Commission: {result.config.commission_pct:.2%} | "
                      f"Slippage: {result.config.slippage_pct:.2%}").replace(",", ",")
        pdf.cell(0, 5, f"Params: {params_str}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, config_str, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(30, 30, 60)
        pdf.ln(2)

    def _add_metrics_table(self, pdf: FPDF, m: PerformanceMetrics):
        """Two-column metrics table."""
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 240, 245)

        left = [
            ("Total Return", f"{m.total_return:.2%}"),
            ("CAGR", f"{m.cagr:.2%}"),
            ("Sharpe Ratio", f"{m.sharpe_ratio:.2f}"),
            ("Sortino Ratio", f"{m.sortino_ratio:.2f}"),
            ("Calmar Ratio", f"{m.calmar_ratio:.2f}"),
            ("Volatility", f"{m.volatility:.2%}"),
            ("Max Drawdown", f"{m.max_drawdown:.2%}"),
            ("Max DD Duration", f"{m.max_drawdown_duration_days}d"),
            ("VaR 95%", f"{m.var_95:.4f}"),
            ("CVaR 95%", f"{m.cvar_95:.4f}"),
        ]
        right = [
            ("Total Trades", str(m.total_trades)),
            ("Win Rate", f"{m.win_rate:.1%}"),
            ("Profit Factor", f"{m.profit_factor:.2f}"),
            ("Avg Trade P&L", f"{m.avg_trade_pnl:.2%}"),
            ("Avg Win", f"{m.avg_win:.2%}"),
            ("Avg Loss", f"{m.avg_loss:.2%}"),
            ("Best Trade", f"{m.best_trade:.2%}"),
            ("Worst Trade", f"{m.worst_trade:.2%}"),
            ("Avg Hold Days", f"{m.avg_holding_days:.1f}"),
            ("Alpha / Beta", f"{m.alpha:.2%} / {m.beta:.2f}"),
        ]

        for i in range(len(left)):
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(32, 5, left[i][0], border=1, fill=True)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(25, 5, left[i][1], border=1, align="R")
            pdf.cell(10, 5, "")  # spacer
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(32, 5, right[i][0], border=1, fill=True)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(25, 5, right[i][1], border=1, align="R")
            pdf.ln()

    def _add_trades_table(self, pdf: FPDF, trades_df):
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(240, 240, 245)

        headers = ["Entry", "Exit", "Side", "Entry $", "Exit $", "P&L %", "Days"]
        widths = [28, 28, 16, 24, 24, 20, 16]

        for h, w in zip(headers, widths):
            pdf.cell(w, 6, h, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 7)
        for _, t in trades_df.iterrows():
            entry_d = t["entry_date"].strftime("%Y-%m-%d") if hasattr(t["entry_date"], "strftime") else str(t["entry_date"])[:10]
            exit_d = t["exit_date"].strftime("%Y-%m-%d") if hasattr(t["exit_date"], "strftime") else str(t["exit_date"])[:10]
            row = [
                entry_d,
                exit_d,
                t["side"],
                f"{t['entry_price']:.2f}",
                f"{t['exit_price']:.2f}",
                f"{t['pnl_pct']:.2%}",
                str(int(t["duration_days"])),
            ]
            for val, w in zip(row, widths):
                pdf.cell(w, 5, val, border=1, align="C")
            pdf.ln()
