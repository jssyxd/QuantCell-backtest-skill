"""
SMC 策略模块

实现完整的 SMC 交易策略，包括:
- 风险管理 (SL/TP/仓位计算)
- 订单管理
- 信号生成

基于 DeFiers-SMC Strategy v0.4.0 Pine Script 翻译
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from .indicators import (
    SMCConfig, compute_smc_indicators, get_signals
)

logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    """交易方向"""
    FLAT = 0
    LONG = 1
    SHORT = -1


@dataclass
class Trade:
    """交易记录"""
    entry_time: pd.Timestamp
    entry_price: float
    direction: TradeDirection
    size: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None
    score: float = 0.0
    factors: int = 0


@dataclass
class BacktestResult:
    """回测结果"""
    trades: List[Trade]
    equity_curve: List[float]
    initial_cash: float
    final_cash: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float

    def summary(self) -> Dict:
        """生成回测摘要"""
        return {
            'initial_cash': self.initial_cash,
            'final_cash': self.final_cash,
            'total_return': (self.final_cash - self.initial_cash) / self.initial_cash * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate * 100,
            'profit_factor': self.profit_factor,
            'max_drawdown': self.max_drawdown * 100,
            'sharpe_ratio': self.sharpe_ratio,
        }


class SMCStrategy:
    """
    SMC 交易策略

    实现:
    - 5 因子 Smart Money Score 信号
    - 结构化止损/止盈
    - 仓位管理
    - 回测引擎
    """

    def __init__(
        self,
        config: Optional[SMCConfig] = None,
        initial_cash: float = 10000.0,
        commission: float = 0.0005,  # 0.05%
        risk_pct: float = 2.0,
    ):
        self.config = config or SMCConfig()
        self.initial_cash = initial_cash
        self.commission = commission
        self.risk_pct = risk_pct

        # 状态
        self.position = TradeDirection.FLAT
        self.position_size = 0.0
        self.entry_price = 0.0
        self.entry_time: Optional[pd.Timestamp] = None
        self.planned_sl = 0.0
        self.take_profit_1 = 0.0
        self.take_profit_2 = 0.0
        self.tp1_hit = False

        # 资金
        self.cash = initial_cash
        self.equity_curve = [initial_cash]

        # 交易记录
        self.trades: List[Trade] = []
        self.current_trade: Optional[Trade] = None

        # 数据
        self.data: Optional[pd.DataFrame] = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        准备数据，计算 SMC 指标

        Args:
            df: K 线数据

        Returns:
            DataFrame: 带 SMC 指标的数据
        """
        self.data = compute_smc_indicators(df, self.config)
        logger.info(f"数据准备完成: {len(self.data)} 条数据")
        return self.data

    def compute_position_size(self, stop_distance: float) -> float:
        """计算仓位大小"""
        if stop_distance <= 0:
            return 0.0

        risk_amount = self.cash * (self.risk_pct / 100.0)
        size = risk_amount / stop_distance

        # 检查最大止损比例
        max_stop_pct = 5.0
        max_stop_distance = self.data['Close'].iloc[-1] * (max_stop_pct / 100.0)

        if stop_distance > max_stop_distance:
            return 0.0

        return size

    def compute_sl_tp(self, idx: int, direction: TradeDirection) -> Tuple[float, float, float]:
        """计算止损和止盈价格"""
        atr = self.data['ATR'].iloc[idx]
        close = self.data['Close'].iloc[idx]
        buffer = self.config.sl_buffer_atr * atr

        # 从 DataFrame 获取 HH/LL
        hh = self.data['HH'].iloc[idx]
        ll = self.data['LL'].iloc[idx]

        if direction == TradeDirection.LONG:
            # 止损: 最低点 - buffer
            sl = (ll if not np.isnan(ll) else close) - buffer
            stop_distance = close - sl
            tp1 = close + self.config.rr_tp1 * stop_distance
            tp2 = close + self.config.rr_tp2 * stop_distance

        else:  # SHORT
            sl = (hh if not np.isnan(hh) else close) + buffer
            stop_distance = sl - close
            tp1 = close - self.config.rr_tp1 * stop_distance
            tp2 = close - self.config.rr_tp2 * stop_distance

        return sl, tp1, tp2

    def run_backtest(self) -> BacktestResult:
        """运行回测"""
        if self.data is None:
            raise ValueError("请先调用 prepare_data 准备数据")

        logger.info(f"开始回测: {len(self.data)} 条数据")

        # 重置状态
        self.cash = self.initial_cash
        self.equity_curve = [self.initial_cash]
        self.trades = []
        self.position = TradeDirection.FLAT
        self.position_size = 0.0

        # 逐条处理
        for idx in range(len(self.data)):
            self._process_bar(idx)

        # 关闭未平仓的交易
        if self.position != TradeDirection.FLAT:
            self._close_trade(self.data.index[-1], self.data['Close'].iloc[-1], "END_OF_DATA")

        return self._generate_result()

    def _process_bar(self, idx: int):
        """处理单个 K 线"""
        row = self.data.iloc[idx]
        timestamp = self.data.index[idx]
        close = row['Close']
        high = row['High']
        low = row['Low']

        # 如果有持仓，检查止损/止盈
        if self.position != TradeDirection.FLAT:
            # TP1 检查
            if not self.tp1_hit:
                if self.position == TradeDirection.LONG and high >= self.take_profit_1:
                    self._partial_close(timestamp, self.take_profit_1, "TP1")
                elif self.position == TradeDirection.SHORT and low <= self.take_profit_1:
                    self._partial_close(timestamp, self.take_profit_1, "TP1")

            # TP2 检查
            if self.position == TradeDirection.LONG and high >= self.take_profit_2:
                self._close_trade(timestamp, self.take_profit_2, "TP2")
            elif self.position == TradeDirection.SHORT and low <= self.take_profit_2:
                self._close_trade(timestamp, self.take_profit_2, "TP2")

            # 止损检查
            if self.position == TradeDirection.LONG and low <= self.planned_sl:
                self._close_trade(timestamp, self.planned_sl, "STOP_LOSS")
            elif self.position == TradeDirection.SHORT and high >= self.planned_sl:
                self._close_trade(timestamp, self.planned_sl, "STOP_LOSS")

            # Early BE 检查
            if self.config.use_early_be and not self.tp1_hit:
                entry_price = self.entry_price
                stop_dist = abs(entry_price - self.planned_sl)
                if self.position == TradeDirection.LONG:
                    mfe = (high - entry_price) / entry_price
                    trigger = self.config.early_be_rr * stop_dist / entry_price
                    if mfe >= trigger:
                        self.planned_sl = entry_price
                elif self.position == TradeDirection.SHORT:
                    mfe = (entry_price - low) / entry_price
                    trigger = self.config.early_be_rr * stop_dist / entry_price
                    if mfe >= trigger:
                        self.planned_sl = entry_price

        # 检查开仓信号
        if self.position == TradeDirection.FLAT:
            score_long = row['ScoreLong']
            score_short = row['ScoreShort']
            factors_long = row['FactorsLong']
            factors_short = row['FactorsShort']

            # LONG 信号
            if (score_long >= self.config.entry_threshold and
                factors_long >= self.config.require_factors):
                self._open_position(idx, TradeDirection.LONG, score_long, factors_long)

            # SHORT 信号
            elif (score_short >= self.config.entry_threshold and
                  factors_short >= self.config.require_factors):
                self._open_position(idx, TradeDirection.SHORT, score_short, factors_short)

        # 更新权益曲线
        if self.position != TradeDirection.FLAT:
            if self.position == TradeDirection.LONG:
                unrealized_pnl = self.position_size * (close - self.entry_price) - self.position_size * close * self.commission
            else:
                unrealized_pnl = self.position_size * (self.entry_price - close) - self.position_size * close * self.commission

            current_equity = self.cash + unrealized_pnl
        else:
            current_equity = self.cash

        self.equity_curve.append(current_equity)

    def _open_position(self, idx: int, direction: TradeDirection, score: float, factors: int):
        """开仓"""
        close = self.data['Close'].iloc[idx]
        timestamp = self.data.index[idx]

        sl, tp1, tp2 = self.compute_sl_tp(idx, direction)

        # 计算仓位大小
        if direction == TradeDirection.LONG:
            stop_distance = close - sl
        else:
            stop_distance = sl - close

        size = self.compute_position_size(stop_distance)

        if size <= 0:
            return

        # 更新状态
        self.position = direction
        self.position_size = size
        self.entry_price = close
        self.entry_time = timestamp
        self.planned_sl = sl
        self.take_profit_1 = tp1
        self.take_profit_2 = tp2
        self.tp1_hit = False

        # 扣除手续费
        cost = size * close * self.commission
        self.cash -= cost

        # 创建交易记录
        self.current_trade = Trade(
            entry_time=timestamp,
            entry_price=close,
            direction=direction,
            size=size,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            score=score,
            factors=factors,
        )

        logger.debug(f"开仓: {direction.name} @ {close:.2f}, SL={sl:.2f}, TP1={tp1:.2f}, TP2={tp2:.2f}")

    def _partial_close(self, timestamp: pd.Timestamp, price: float, reason: str):
        """部分平仓 (TP1)"""
        if self.position == TradeDirection.LONG:
            pnl = self.position_size * (price - self.entry_price)
        else:
            pnl = self.position_size * (self.entry_price - price)

        # 扣除手续费
        cost = self.position_size * price * self.commission
        pnl -= cost

        self.cash += pnl

        # 更新 TP1 命中状态
        self.tp1_hit = True
        self.planned_sl = self.entry_price  # 移动到 break-even

        logger.debug(f"TP1 部分平仓: {reason} @ {price:.2f}, PnL={pnl:.2f}")

    def _close_trade(self, timestamp: pd.Timestamp, price: float, reason: str):
        """平仓"""
        if self.position == TradeDirection.FLAT:
            return

        if self.position == TradeDirection.LONG:
            pnl = self.position_size * (price - self.entry_price)
        else:
            pnl = self.position_size * (self.entry_price - price)

        # 扣除手续费
        cost = self.position_size * price * self.commission
        pnl -= cost

        self.cash += pnl

        # 记录交易
        if self.current_trade:
            self.current_trade.exit_time = timestamp
            self.current_trade.exit_price = price
            self.current_trade.pnl = pnl
            self.current_trade.pnl_pct = pnl / (self.position_size * self.entry_price) * 100
            self.current_trade.exit_reason = reason
            self.trades.append(self.current_trade)

        logger.debug(f"平仓: {reason} @ {price:.2f}, PnL={pnl:.2f}")

        # 重置状态
        self.position = TradeDirection.FLAT
        self.position_size = 0.0
        self.entry_price = 0.0
        self.entry_time = None
        self.current_trade = None

    def _generate_result(self) -> BacktestResult:
        """生成回测结果"""
        if not self.trades:
            return BacktestResult(
                trades=[],
                equity_curve=self.equity_curve,
                initial_cash=self.initial_cash,
                final_cash=self.cash,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                profit_factor=0.0,
            )

        # 计算统计数据
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl <= 0]

        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0.0

        # 计算最大回撤
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0.0

        # 计算夏普比率
        returns = np.diff(equity) / equity[:-1]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 0 and np.std(returns) > 0 else 0.0

        # 计算盈亏比
        total_win = sum(t.pnl for t in winning_trades) if winning_trades else 0.0
        total_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0.0
        profit_factor = total_win / total_loss if total_loss > 0 else 0.0

        return BacktestResult(
            trades=self.trades,
            equity_curve=self.equity_curve,
            initial_cash=self.initial_cash,
            final_cash=self.cash,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=self.cash - self.initial_cash,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
        )


def run_smc_backtest(
    df: pd.DataFrame,
    config: Optional[SMCConfig] = None,
    initial_cash: float = 10000.0,
    commission: float = 0.0005,
    risk_pct: float = 2.0,
) -> BacktestResult:
    """运行 SMC 回测的便捷函数"""
    strategy = SMCStrategy(config, initial_cash, commission, risk_pct)
    strategy.prepare_data(df)
    return strategy.run_backtest()