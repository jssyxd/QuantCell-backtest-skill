"""
DuckDB 加速数据加载器

使用 DuckDB 直接查询 Parquet 文件，比 pandas 逐文件读取快 10-50 倍。
支持多核并行查询，适合大规模历史数据。

性能对比:
- pandas 逐文件读取: ~100K bars/sec
- DuckDB 查询: ~1M+ bars/sec
"""

import duckdb
from pathlib import Path
from typing import Optional, List, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# 数据根目录
DATA_ROOT = Path("/home/da/桌面/multi-asset-ohlcv/cloud_bundle")

# 币种映射
SYMBOL_MAP = {
    "BTCUSDT": "BTCUSDTraw_data",
    "ETHUSDT": "ETHUSDTraw_data",
    "BNBUSDT": "BNBUSDTraw_data",
    "SOLUSDT": "SOLUSDTraw_data",
}

# 周期映射
INTERVAL_MAP = {
    "1m": "1m",
    "15m": "15m",
    "1h": "1h",
}


class DuckDBDataLoader:
    """DuckDB 加速数据加载器"""

    def __init__(self, base_dir: Optional[Path] = None, threads: int = 4):
        """
        初始化 DuckDB 数据加载器

        Args:
            base_dir: 数据根目录
            threads: DuckDB 并行线程数
        """
        self.base_dir = base_dir or DATA_ROOT
        self.threads = threads
        self.con = None
        self._init_connection()

    def _init_connection(self):
        """初始化 DuckDB 连接"""
        self.con = duckdb.connect(database=":memory:")
        self.con.execute(f"SET threads TO {self.threads};")
        # 安装 parquet 扩展
        try:
            self.con.execute("INSTALL parquet;")
        except:
            pass  # 已安装
        self.con.execute("LOAD parquet;")
        logger.info(f"DuckDB 连接初始化完成, threads={self.threads}")

    def _get_parquet_pattern(self, symbol: str, interval: str) -> str:
        """获取 Parquet 文件通配符路径"""
        if symbol not in SYMBOL_MAP:
            raise ValueError(f"不支持的币种: {symbol}")
        if interval not in INTERVAL_MAP:
            raise ValueError(f"不支持的周期: {interval}")

        folder = SYMBOL_MAP[symbol]
        tf = INTERVAL_MAP[interval]
        pattern = str(self.base_dir / folder / "ohlcv" / tf / f"*_{tf}_ohlcv_*.parquet")
        return pattern

    def load(
        self,
        symbol: str,
        interval: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        使用 DuckDB 加载 K 线数据

        Args:
            symbol: 币种
            interval: 周期
            start: 开始时间 (YYYY-MM-DD)
            end: 结束时间 (YYYY-MM-DD)
            columns: 要读取的列 (None=全部)

        Returns:
            pd.DataFrame: K 线数据
        """
        pattern = self._get_parquet_pattern(symbol, interval)

        # 构建查询
        cols = "*" if columns is None else ", ".join(columns)
        query = f"""
            SELECT {cols}
            FROM read_parquet('{pattern}')
            WHERE 1=1
        """

        params = []
        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)

        query += " ORDER BY timestamp"

        # 执行查询
        logger.info(f"DuckDB 查询: {symbol} {interval} ({start} ~ {end})")
        result = self.con.execute(query, params)
        df = result.fetchdf()

        # 标准化
        df = self._normalize(df)

        logger.info(f"加载完成: {len(df):,} 条, {df.index[0]} ~ {df.index[-1]}")
        return df

    def load_multiple(
        self,
        symbols: List[str],
        intervals: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> dict:
        """批量加载"""
        result = {}
        for symbol in symbols:
            for interval in intervals:
                try:
                    df = self.load(symbol, interval, start, end)
                    result[(symbol, interval)] = df
                except Exception as e:
                    logger.error(f"加载失败: {symbol} {interval}: {e}")
        return result

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化 DataFrame"""
        df = df.copy()

        # 列名标准化
        rename_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low',
            'close': 'Close', 'volume': 'Volume'
        }
        df = df.rename(columns=rename_map)

        # 时间索引
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')

        # 数据类型
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = df[col].astype('float64')

        return df

    def close(self):
        """关闭 DuckDB 连接"""
        if self.con:
            self.con.close()
            self.con = None

    def __del__(self):
        self.close()


# 便捷函数
def load_klines_duckdb(
    symbol: str,
    interval: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    threads: int = 4,
) -> pd.DataFrame:
    """使用 DuckDB 加载 K 线数据"""
    loader = DuckDBDataLoader(threads=threads)
    try:
        return loader.load(symbol, interval, start, end)
    finally:
        loader.close()


def load_all_symbols_duckdb(
    intervals: List[str] = ["1m", "15m", "1h"],
    start: Optional[str] = None,
    end: Optional[str] = None,
    threads: int = 4,
) -> dict:
    """使用 DuckDB 加载所有币种"""
    loader = DuckDBDataLoader(threads=threads)
    try:
        return loader.load_multiple(
            symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
            intervals=intervals,
            start=start,
            end=end,
        )
    finally:
        loader.close()