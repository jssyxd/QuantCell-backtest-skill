"""
SMC 核心指标模块 (向量化优化版)

实现 Smart Money Concepts 策略的核心指标:
- 枢轴点检测 (Pivots)
- Order Blocks (订单块)
- Fair Value Gaps (公允价值缺口)
- Liquidity Zones (流动性区域)
- HTF Bias (高时间框架偏斜)
- Premium/Discount zones
- Smart Money Score (智能货币评分)

基于 DeFiers-SMC Strategy v0.4.0 Pine Script 翻译
优化: 使用 NumPy/Pandas 向量化操作提升性能
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrendState(Enum):
    """趋势状态"""
    UNKNOWN = 0
    BULLISH = 1
    BEARISH = -1


@dataclass
class SMCConfig:
    """SMC 策略配置"""
    # 枢轴检测
    swing_len: int = 10
    mss_disp_mult: float = 1.5

    # Order Blocks
    vol_mult: float = 1.5
    fvg_min_atr: float = 0.5
    ob_max_age: int = 60
    fvg_max_age: int = 80
    max_obs: int = 15
    max_fvgs: int = 20
    ob_lookback: int = 20

    # Liquidity
    liq_range_pct: float = 0.15
    max_liq_levels: int = 15
    sweep_recency_bars: int = 15

    # Confluence & Entry
    entry_threshold: float = 65
    require_factors: int = 3
    htf_bias_filter: bool = True

    # Risk
    risk_pct: float = 2.0
    sl_buffer_atr: float = 0.5
    rr_tp1: float = 1.5
    rr_tp2: float = 3.0
    tp1_qty_pct: float = 50.0
    use_trailing: bool = True
    use_early_be: bool = True
    early_be_rr: float = 0.7

    # Regime
    enable_regime: bool = True
    regime_hi: float = 1.5
    regime_lo: float = 0.7
    regime_adj_pct: float = 20.0


def compute_smc_indicators(df: pd.DataFrame, config: Optional[SMCConfig] = None) -> pd.DataFrame:
    """
    向量化计算 SMC 指标 (高性能版本)

    Args:
        df: K 线数据，索引为 DatetimeIndex，列包含 Open/High/Low/Close/Volume
        config: SMC 配置

    Returns:
        DataFrame: 添加了 SMC 指标的 DataFrame
    """
    config = config or SMCConfig()

    # 标准化列名
    df = df.copy()
    if 'open' in df.columns:
        df = df.rename(columns={
            'open': 'Open', 'high': 'High', 'low': 'Low',
            'close': 'Close', 'volume': 'Volume'
        })

    n = len(df)

    # 1. 基础指标 (ATR, Volume SMA)
    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    open_ = df['Open'].values
    volume = df['Volume'].values

    # True Range
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]

    # ATR (14)
    atr = np.zeros(n)
    atr[0] = tr[0]
    for i in range(1, n):
        atr[i] = (atr[i-1] * 13 + tr[i]) / 14

    df['ATR'] = atr

    # Volume SMA 20
    vol_sma20 = pd.Series(volume).rolling(20, min_periods=1).mean().values

    # ATR 100 (用于 regime)
    atr100 = pd.Series(atr).rolling(100, min_periods=50).mean().ffill().fillna(atr[0]).values

    # 2. 枢轴点检测 (向量化)
    swing_len = config.swing_len

    # 高点: 前后 swing_len 根 K 线没有更高
    is_high = np.zeros(n, dtype=bool)
    for i in range(swing_len, n - swing_len):
        window = high[i - swing_len:i + swing_len + 1]
        if high[i] == np.max(window):
            is_high[i] = True

    # 低点
    is_low = np.zeros(n, dtype=bool)
    for i in range(swing_len, n - swing_len):
        window = low[i - swing_len:i + swing_len + 1]
        if low[i] == np.min(window):
            is_low[i] = True

    # HH (最近的高点) 和 LL (最近的低点)
    hh = np.full(n, np.nan)
    ll = np.full(n, np.nan)
    last_hh_idx = 0
    last_ll_idx = 0

    for i in range(n):
        if is_high[i]:
            hh[i] = high[i]
            last_hh_idx = i
        else:
            hh[i] = hh[last_hh_idx] if last_hh_idx > 0 else np.nan

        if is_low[i]:
            ll[i] = low[i]
            last_ll_idx = i
        else:
            ll[i] = ll[last_ll_idx] if last_ll_idx > 0 else np.nan

    df['HH'] = hh
    df['LL'] = ll

    # 3. 趋势状态 (简化)
    # 使用 EMA 交叉判断趋势
    ema9 = pd.Series(close).ewm(span=9, adjust=False).mean().values
    ema21 = pd.Series(close).ewm(span=21, adjust=False).mean().values

    trend_state = np.zeros(n, dtype=int)  # 0=unknown, 1=bull, -1=bear

    # 初始化: 当 EMA9 > EMA21 时为牛市
    for i in range(1, n):
        if ema9[i] > ema21[i]:
            trend_state[i] = 1
        elif ema9[i] < ema21[i]:
            trend_state[i] = -1
        else:
            trend_state[i] = trend_state[i-1]

    df['TrendState'] = trend_state

    # 4. BOS/CHoCH 检测
    # 当收盘价突破 HH 时为牛市 BOS，突破 LL 时为熊市 BOS
    bull_bos = (close > np.roll(hh, 1)) & (trend_state >= 0)
    bear_bos = (close < np.roll(ll, 1)) & (trend_state <= 0)

    bull_bos[0] = False
    bear_bos[0] = False

    df['BullBOS'] = bull_bos
    df['BearBOS'] = bear_bos

    # 5. HTF Bias (简化: 使用 EMA50)
    ema50 = pd.Series(close).ewm(span=50, adjust=False).mean().values
    htf_bull_bias = close > ema50
    htf_bear_bias = close < ema50

    df['HTFBullBias'] = htf_bull_bias
    df['HTFBearBias'] = htf_bear_bias

    # 6. Order Blocks (简化检测)
    # 在一根下跌 K 线且成交量大于均值时标记 OB
    is_bearish = close < open_
    vol_ratio = volume / np.maximum(vol_sma20, 1e-9)
    bull_ob_signal = is_bearish[1:] & (vol_ratio[1:] >= config.vol_mult)
    bull_ob_signal = np.concatenate([[False], bull_ob_signal])

    is_bullish = close > open_
    bear_ob_signal = is_bullish[1:] & (vol_ratio[1:] >= config.vol_mult)
    bear_ob_signal = np.concatenate([[False], bear_ob_signal])

    df['BullOBSignal'] = bull_ob_signal
    df['BearOBSignal'] = bear_ob_signal

    # 7. Fair Value Gaps
    # 看多 FVG: 当前低点 > 2根前高点
    bull_fvg = (low > np.roll(high, 2)) & ((low - np.roll(high, 2)) >= config.fvg_min_atr * atr)
    bull_fvg[0] = False
    bull_fvg[1] = False

    # 看空 FVG: 当前高点 < 2根前低点
    bear_fvg = (high < np.roll(low, 2)) & ((np.roll(low, 2) - high) >= config.fvg_min_atr * atr)
    bear_fvg[0] = False
    bear_fvg[1] = False

    df['BullFVG'] = bull_fvg
    df['BearFVG'] = bear_fvg

    # 8. Premium/Discount
    # range_top/range_bot 用 HH/LL
    range_top = np.maximum.accumulate(np.where(np.isnan(hh), -np.inf, hh))
    range_bot = np.minimum.accumulate(np.where(np.isnan(ll), np.inf, ll))

    # 替换 -inf/inf
    range_top = np.where(np.isinf(range_top), high, range_top)
    range_bot = np.where(np.isinf(range_bot), low, range_bot)

    equilibrium = (range_top + range_bot) / 2

    df['RangeTop'] = range_top
    df['RangeBot'] = range_bot
    df['Equilibrium'] = equilibrium

    in_discount = close <= equilibrium
    in_premium = close >= equilibrium

    df['InDiscount'] = in_discount
    df['InPremium'] = in_premium

    # 9. Liquidity Sweep (简化: 用突破 HH/LL 检测)
    # BSL sweep: 价格先突破 HH 然后回落
    bsl_swept = np.zeros(n, dtype=bool)
    ssl_swept = np.zeros(n, dtype=bool)

    for i in range(1, n):
        if not np.isnan(hh[i-1]) and high[i] > hh[i-1] and close[i] < hh[i-1]:
            bsl_swept[i] = True
        if not np.isnan(ll[i-1]) and low[i] < ll[i-1] and close[i] > ll[i-1]:
            ssl_swept[i] = True

    df['BSLSwept'] = bsl_swept
    df['SSLSwept'] = ssl_swept

    # 10. Smart Money Score 计算
    # F1: HTF Bias (25%)
    f1_long = htf_bull_bias.astype(float)
    f1_short = htf_bear_bias.astype(float)

    # F2: 本地趋势 (20%)
    f2_long = (trend_state == 1).astype(float)
    f2_short = (trend_state == -1).astype(float)

    # F3: Liquidity Sweep (20%)
    f3_long = ssl_swept.astype(float)
    f3_short = bsl_swept.astype(float)

    # F4: POI (Order Blocks/FVGs) (20%)
    f4_long = bull_ob_signal.astype(float) * 1.0 + bull_fvg.astype(float) * 0.7
    f4_long = np.minimum(f4_long, 1.0)

    f4_short = bear_ob_signal.astype(float) * 1.0 + bear_fvg.astype(float) * 0.7
    f4_short = np.minimum(f4_short, 1.0)

    # F5: Premium/Discount (15%)
    f5_long = in_discount.astype(float)
    f5_short = in_premium.astype(float)

    # 加权分数
    score_long = 100 * (0.25 * f1_long + 0.20 * f2_long + 0.20 * f3_long + 0.20 * f4_long + 0.15 * f5_long)
    score_short = 100 * (0.25 * f1_short + 0.20 * f2_short + 0.20 * f3_short + 0.20 * f4_short + 0.15 * f5_short)

    df['ScoreLong'] = score_long
    df['ScoreShort'] = score_short

    # 活跃因子数量
    factors_long = (f1_long >= 1).astype(int) + (f2_long >= 1).astype(int) + (f3_long >= 1).astype(int) + (f4_long >= 0.5).astype(int) + (f5_long >= 1).astype(int)
    factors_short = (f1_short >= 1).astype(int) + (f2_short >= 1).astype(int) + (f3_short >= 1).astype(int) + (f4_short >= 0.5).astype(int) + (f5_short >= 1).astype(int)

    df['FactorsLong'] = factors_long
    df['FactorsShort'] = factors_short

    return df


def get_signals(df: pd.DataFrame, config: Optional[SMCConfig] = None) -> pd.DataFrame:
    """
    从 SMC 指标 DataFrame 生成交易信号

    Args:
        df: SMC 指标 DataFrame
        config: SMC 配置

    Returns:
        DataFrame: 添加了 Signal 列的 DataFrame
    """
    config = config or SMCConfig()

    df = df.copy()

    # LONG 信号条件
    long_cond = (df['ScoreLong'] >= config.entry_threshold) & (df['FactorsLong'] >= config.require_factors)

    # SHORT 信号条件
    short_cond = (df['ScoreShort'] >= config.entry_threshold) & (df['FactorsShort'] >= config.require_factors)

    # 生成信号
    df['Signal'] = 'NEUTRAL'
    df.loc[long_cond, 'Signal'] = 'LONG'
    df.loc[short_cond, 'Signal'] = 'SHORT'

    return df


class SMCIndicators:
    """SMC 指标计算器 (兼容性封装)"""

    def __init__(self, df: pd.DataFrame, config: Optional[SMCConfig] = None):
        self.df = df
        self.config = config or SMCConfig()

    def run(self) -> pd.DataFrame:
        """运行指标计算"""
        return compute_smc_indicators(self.df, self.config)