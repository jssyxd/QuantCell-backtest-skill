"""
回测引擎模块

运行 SMC 策略回测，支持:
- 多币种、多周期批量回测
- 结果汇总分析
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

from data import ParquetDataLoader
from strategies import SMCStrategy, SMCConfig, BacktestResult

logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    回测运行器

    支持:
    - 多币种、多周期回测
    - 结果汇总
    - 报告生成
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化回测运行器

        Args:
            data_dir: 数据目录路径
        """
        self.data_loader = ParquetDataLoader(data_dir)
        self.results: Dict[str, BacktestResult] = {}
        self.config = SMCConfig()

    def run_single(
        self,
        symbol: str,
        interval: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        initial_cash: float = 10000.0,
    ) -> Tuple[BacktestResult, pd.DataFrame]:
        """
        运行单个币种/周期的回测

        Args:
            symbol: 币种
            interval: 周期
            start: 开始时间
            end: 结束时间
            initial_cash: 初始资金

        Returns:
            Tuple[BacktestResult, pd.DataFrame]: 回测结果和数据
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"回测: {symbol} {interval}")
        logger.info(f"{'='*60}")

        # 加载数据
        df = self.data_loader.load_single(symbol, interval, start, end)
        logger.info(f"加载数据: {len(df)} 条, {df.index[0]} ~ {df.index[-1]}")

        # 运行策略
        strategy = SMCStrategy(self.config, initial_cash)
        strategy.prepare_data(df)
        result = strategy.run_backtest()

        # 保存结果
        key = f"{symbol}_{interval}"
        self.results[key] = result

        # 输出摘要
        summary = result.summary()
        logger.info(f"\n回测结果摘要:")
        logger.info(f"  总交易次数: {summary['total_trades']}")
        logger.info(f"  盈利交易: {summary['winning_trades']}")
        logger.info(f"  亏损交易: {summary['losing_trades']}")
        logger.info(f"  胜率: {summary['win_rate']:.2f}%")
        logger.info(f"  盈亏比: {summary['profit_factor']:.2f}")
        logger.info(f"  最大回撤: {summary['max_drawdown']:.2f}%")
        logger.info(f"  夏普比率: {summary['sharpe_ratio']:.2f}")
        logger.info(f"  总收益: {summary['total_return']:.2f}%")
        logger.info(f"  最终资金: ${summary['final_cash']:.2f}")

        return result, strategy.data

    def run_batch(
        self,
        symbols: List[str],
        intervals: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        initial_cash: float = 10000.0,
    ) -> Dict[str, BacktestResult]:
        """
        批量回测

        Args:
            symbols: 币种列表
            intervals: 周期列表
            start: 开始时间
            end: 结束时间
            initial_cash: 初始资金

        Returns:
            Dict[str, BacktestResult]: 所有回测结果
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"批量回测: {len(symbols)} 个币种 x {len(intervals)} 个周期")
        logger.info(f"{'='*60}")

        for symbol in symbols:
            for interval in intervals:
                try:
                    result, _ = self.run_single(symbol, interval, start, end, initial_cash)
                except Exception as e:
                    logger.error(f"回测失败: {symbol} {interval}: {e}")

        return self.results

    def summary_all(self) -> pd.DataFrame:
        """
        生成所有回测结果的汇总表

        Returns:
            pd.DataFrame: 汇总表
        """
        rows = []
        for key, result in self.results.items():
            summary = result.summary()
            rows.append({
                'symbol_interval': key,
                'initial_cash': summary['initial_cash'],
                'final_cash': summary['final_cash'],
                'total_return_pct': summary['total_return'],
                'total_trades': summary['total_trades'],
                'win_rate_pct': summary['win_rate'],
                'profit_factor': summary['profit_factor'],
                'max_drawdown_pct': summary['max_drawdown'],
                'sharpe_ratio': summary['sharpe_ratio'],
            })

        df = pd.DataFrame(rows)
        return df

    def print_summary(self):
        """打印汇总结果"""
        df = self.summary_all()
        print("\n" + "="*100)
        print("回测结果汇总")
        print("="*100)
        print(df.to_string(index=False))
        print("="*100)


def run_full_backtest(
    symbols: List[str] = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
    intervals: List[str] = ["1m", "15m", "1h"],
    start: Optional[str] = None,
    end: Optional[str] = None,
    initial_cash: float = 10000.0,
) -> Dict[str, BacktestResult]:
    """
    运行完整回测的便捷函数

    Args:
        symbols: 币种列表
        intervals: 周期列表
        start: 开始时间
        end: 结束时间
        initial_cash: 初始资金

    Returns:
        Dict[str, BacktestResult]: 所有回测结果
    """
    runner = BacktestRunner()
    return runner.run_batch(symbols, intervals, start, end, initial_cash)