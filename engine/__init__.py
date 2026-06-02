"""
__init__.py for engine module
"""
from .backtest_runner import BacktestRunner, run_full_backtest
from .report_generator import generate_html_report, save_html_report, export_trades_to_csv, export_results_to_json
from .vector_engine import vector_backtest, VectorBacktestResult
from .parallel_runner import ParallelBacktestRunner, run_parallel_backtest

__all__ = [
    "BacktestRunner",
    "run_full_backtest",
    "generate_html_report",
    "save_html_report",
    "export_trades_to_csv",
    "export_results_to_json",
    "vector_backtest",
    "VectorBacktestResult",
    "ParallelBacktestRunner",
    "run_parallel_backtest",
]