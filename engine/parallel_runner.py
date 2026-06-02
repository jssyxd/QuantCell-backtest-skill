"""
并行回测运行器

使用 multiprocessing 并行运行多个回测任务。
支持多币种、多周期同时回测。

性能:
- 单核: ~30 分钟 (4 币种 × 3 周期 × 全量数据)
- 4 核并行: ~8-10 分钟
- 8 核并行: ~4-5 分钟
"""

import multiprocessing as mp
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import time

from data import ParquetDataLoader
from strategies import SMCConfig
from engine.vector_engine import vector_backtest, VectorBacktestResult

logger = logging.getLogger(__name__)


def _run_single_backtest(args: Tuple) -> Tuple[str, VectorBacktestResult]:
    """单个回测任务 (用于 multiprocessing)"""
    symbol, interval, start, end, config_dict, initial_cash, commission, risk_pct = args

    try:
        # 在子进程中重新创建配置
        config = SMCConfig(**config_dict)

        # 加载数据
        loader = ParquetDataLoader()
        df = loader.load_single(symbol, interval, start=start, end=end)

        # 运行向量化回测
        result = vector_backtest(
            df,
            config=config,
            initial_cash=initial_cash,
            commission=commission,
            risk_pct=risk_pct,
        )

        key = f"{symbol}_{interval}"
        return key, result

    except Exception as e:
        key = f"{symbol}_{interval}"
        logger.error(f"回测失败: {key}: {e}")
        return key, None


class ParallelBacktestRunner:
    """并行回测运行器"""

    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化并行运行器

        Args:
            max_workers: 最大并行数 (None=CPU 核数)
        """
        self.max_workers = max_workers or mp.cpu_count()
        logger.info(f"并行运行器初始化: {self.max_workers} workers")

    def run_batch(
        self,
        symbols: List[str],
        intervals: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        config: Optional[SMCConfig] = None,
        initial_cash: float = 10000.0,
        commission: float = 0.0005,
        risk_pct: float = 2.0,
    ) -> Dict[str, VectorBacktestResult]:
        """
        并行运行多个回测

        Args:
            symbols: 币种列表
            intervals: 周期列表
            start: 开始时间
            end: 结束时间
            config: SMC 配置
            initial_cash: 初始资金
            commission: 手续费率
            risk_pct: 每笔风险

        Returns:
            Dict[str, VectorBacktestResult]: 回测结果
        """
        config = config or SMCConfig()

        # 构建任务列表
        tasks = []
        for symbol in symbols:
            for interval in intervals:
                task_args = (
                    symbol, interval, start, end,
                    {
                        'entry_threshold': config.entry_threshold,
                        'require_factors': config.require_factors,
                        'swing_len': config.swing_len,
                        'vol_mult': config.vol_mult,
                        'fvg_min_atr': config.fvg_min_atr,
                        'ob_max_age': config.ob_max_age,
                        'liq_range_pct': config.liq_range_pct,
                        'sl_buffer_atr': config.sl_buffer_atr,
                        'rr_tp1': config.rr_tp1,
                        'rr_tp2': config.rr_tp2,
                        'risk_pct': config.risk_pct,
                    },
                    initial_cash, commission, risk_pct,
                )
                tasks.append(task_args)

        total = len(tasks)
        print(f"\n🚀 启动并行回测: {total} 个任务, {self.max_workers} workers")
        print(f"   币种: {', '.join(symbols)}")
        print(f"   周期: {', '.join(intervals)}")
        print(f"   时间: {start} ~ {end}")
        print("="*60)

        start_time = time.time()
        results = {}

        # 并行执行
        with mp.Pool(processes=self.max_workers) as pool:
            for i, (key, result) in enumerate(pool.imap_unordered(_run_single_backtest, tasks), 1):
                if result is not None:
                    results[key] = result
                    ret = result.total_return * 100
                    print(f"  [{i}/{total}] {key}: {result.total_trades} trades | WR={result.win_rate*100:.1f}% | PF={result.profit_factor:.2f} | Ret={ret:.1f}%")
                else:
                    print(f"  [{i}/{total}] {key}: FAILED")

        elapsed = time.time() - start_time
        print(f"\n✅ 并行回测完成: {len(results)}/{total} 成功, 耗时 {elapsed:.1f}s")

        return results


def run_parallel_backtest(
    symbols: List[str] = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
    intervals: List[str] = ["1m", "15m", "1h"],
    start: Optional[str] = None,
    end: Optional[str] = None,
    config: Optional[SMCConfig] = None,
    max_workers: Optional[int] = None,
) -> Dict[str, VectorBacktestResult]:
    """并行回测便捷函数"""
    runner = ParallelBacktestRunner(max_workers)
    return runner.run_batch(symbols, intervals, start, end, config)