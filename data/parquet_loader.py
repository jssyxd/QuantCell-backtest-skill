"""
Parquet 数据加载器

从 JasonleeQAQ/multi-asset-ohlcv 数据集加载 K 线数据。
支持多币种、多周期、跨文件拼接。
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 数据根目录
DATA_ROOT = Path("/home/da/桌面/multi-asset-ohlcv/cloud_bundle")

# 币种映射: symbol -> folder_name
SYMBOL_MAP = {
    "BTCUSDT": "BTCUSDTraw_data",
    "ETHUSDT": "ETHUSDTraw_data",
    "BNBUSDT": "BNBUSDTraw_data",
    "SOLUSDT": "SOLUSDTraw_data",
}

# 周期映射: interval -> folder_name
INTERVAL_MAP = {
    "1m": "1m",
    "15m": "15m",
    "1h": "1h",
}


class ParquetDataLoader:
    """Parquet 数据加载器"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or DATA_ROOT
        self._validate_base_dir()

    def _validate_base_dir(self):
        """验证数据目录存在"""
        if not self.base_dir.exists():
            raise FileNotFoundError(f"数据目录不存在: {self.base_dir}")

    def get_data_path(self, symbol: str, interval: str) -> Path:
        """获取数据目录路径"""
        if symbol not in SYMBOL_MAP:
            raise ValueError(f"不支持的币种: {symbol}, 支持: {list(SYMBOL_MAP.keys())}")
        if interval not in INTERVAL_MAP:
            raise ValueError(f"不支持的周期: {interval}, 支持: {list(INTERVAL_MAP.keys())}")

        folder = SYMBOL_MAP[symbol]
        folder_path = self.base_dir / folder / "ohlcv" / INTERVAL_MAP[interval]

        if not folder_path.exists():
            raise FileNotFoundError(f"数据目录不存在: {folder_path}")

        return folder_path

    def load_single(
        self,
        symbol: str,
        interval: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        加载单个币种的 K 线数据

        Args:
            symbol: 币种符号 (如 BTCUSDT)
            interval: 周期 (如 1m, 15m, 1h)
            start: 开始时间 (YYYY-MM-DD)
            end: 结束时间 (YYYY-MM-DD)

        Returns:
            pd.DataFrame: K 线数据，索引为 DatetimeIndex
        """
        folder_path = self.get_data_path(symbol, interval)

        # 获取所有 Parquet 文件
        pattern = f"{symbol}_{interval}_ohlcv_*.parquet"
        files = sorted(folder_path.glob(pattern))

        if not files:
            raise FileNotFoundError(f"未找到数据文件: {folder_path}/{pattern}")

        logger.info(f"找到 {len(files)} 个数据文件: {files[0].name} ~ {files[-1].name}")

        # 读取并拼接
        dfs = []
        for f in files:
            df = pd.read_parquet(f)
            dfs.append(df)

        result = pd.concat(dfs, axis=0)
        result = result.sort_index()

        # 时间范围筛选
        if start:
            start_dt = pd.to_datetime(start)
            result = result[result.index >= start_dt]
        if end:
            end_dt = pd.to_datetime(end)
            result = result[result.index <= end_dt]

        # 标准化列名
        result = self._normalize_columns(result)

        logger.info(f"加载 {symbol} {interval}: {len(result)} 条数据, {result.index[0]} ~ {result.index[-1]}")

        return result

    def load_multiple(
        self,
        symbols: List[str],
        intervals: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> dict:
        """
        批量加载多个币种/周期的数据

        Args:
            symbols: 币种列表
            intervals: 周期列表
            start: 开始时间
            end: 结束时间

        Returns:
            dict: {(symbol, interval): DataFrame, ...}
        """
        result = {}
        errors = []

        for symbol in symbols:
            for interval in intervals:
                try:
                    df = self.load_single(symbol, interval, start, end)
                    result[(symbol, interval)] = df
                except Exception as e:
                    logger.error(f"加载失败: {symbol} {interval}: {e}")
                    errors.append((symbol, interval, str(e)))

        if errors:
            logger.warning(f"加载失败 {len(errors)} 个: {errors}")

        return result

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名为大写"""
        df = df.copy()
        rename_map = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        }
        df = df.rename(columns=rename_map)
        return df

    def list_available_files(self, symbol: str, interval: str) -> List[Path]:
        """列出可用文件"""
        folder_path = self.get_data_path(symbol, interval)
        pattern = f"{symbol}_{interval}_ohlcv_*.parquet"
        return sorted(folder_path.glob(pattern))

    def get_date_range(self, symbol: str, interval: str) -> Tuple[str, str]:
        """获取数据的日期范围"""
        files = self.list_available_files(symbol, interval)
        if not files:
            raise ValueError(f"未找到 {symbol} {interval} 的数据文件")

        # 从文件名提取日期范围
        dates = []
        for f in files:
            name = f.stem  # e.g., BTCUSDT_1m_ohlcv_2025-01
            parts = name.split('_')
            if len(parts) >= 4:
                date_str = parts[-1]  # e.g., 2025-01
                dates.append(date_str)

        if dates:
            return min(dates), max(dates)
        return None, None


# 便捷函数
def load_klines(
    symbol: str,
    interval: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """加载 K 线数据的便捷函数"""
    loader = ParquetDataLoader()
    return loader.load_single(symbol, interval, start, end)


def load_all_symbols(
    intervals: List[str] = ["1m", "15m", "1h"],
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> dict:
    """加载所有 4 个币种的数据"""
    loader = ParquetDataLoader()
    return loader.load_multiple(
        symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
        intervals=intervals,
        start=start,
        end=end,
    )