"""
SMC 回测系统测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data import ParquetDataLoader
from strategies import SMCConfig, compute_smc_indicators, run_smc_backtest


def test_data_loading():
    """测试数据加载"""
    print("\n" + "="*60)
    print("测试 1: 数据加载")
    print("="*60)

    loader = ParquetDataLoader()

    # 测试加载 BTC 1m 数据 (只加载一个月用于快速测试)
    df = loader.load_single("BTCUSDT", "1m", start="2025-01-01", end="2025-01-31")

    print(f"✅ 数据加载成功: {len(df)} 条")
    print(f"   时间范围: {df.index[0]} ~ {df.index[-1]}")
    print(f"   列: {list(df.columns)}")

    return df


def test_smc_indicators(df):
    """测试 SMC 指标计算"""
    print("\n" + "="*60)
    print("测试 2: SMC 指标计算")
    print("="*60)

    result = compute_smc_indicators(df)

    print(f"✅ SMC 指标计算完成")
    print(f"   ScoreLong 范围: {result['ScoreLong'].min():.1f} ~ {result['ScoreLong'].max():.1f}")
    print(f"   ScoreShort 范围: {result['ScoreShort'].min():.1f} ~ {result['ScoreShort'].max():.1f}")

    # 检查有多少条 LONG/SHORT 信号
    long_signals = (result['ScoreLong'] >= 65).sum()
    short_signals = (result['ScoreShort'] >= 65).sum()
    print(f"   LONG 信号数量: {long_signals}")
    print(f"   SHORT 信号数量: {short_signals}")

    return result


def test_backtest():
    """测试回测功能"""
    print("\n" + "="*60)
    print("测试 3: 回测功能")
    print("="*60)

    # 加载少量数据用于测试
    loader = ParquetDataLoader()
    df = loader.load_single("BTCUSDT", "15m", start="2025-01-01", end="2025-03-31")

    # 运行回测
    result = run_smc_backtest(df, initial_cash=10000.0, risk_pct=2.0)

    print(f"✅ 回测完成")
    print(f"   总交易次数: {result.total_trades}")
    print(f"   盈利交易: {result.winning_trades}")
    print(f"   亏损交易: {result.losing_trades}")
    print(f"   胜率: {result.win_rate * 100:.2f}%")
    print(f"   盈亏比: {result.profit_factor:.2f}")
    print(f"   最大回撤: {result.max_drawdown * 100:.2f}%")
    print(f"   最终资金: ${result.final_cash:.2f}")

    # 显示交易详情
    if result.trades:
        print("\n前 5 笔交易:")
        for i, trade in enumerate(result.trades[:5]):
            exit_price_str = f"{trade.exit_price:.2f}" if trade.exit_price else "N/A"
            print(f"   {i+1}. {trade.direction.name} @ {trade.entry_price:.2f} -> {exit_price_str} | PnL: {trade.pnl:.2f} | 原因: {trade.exit_reason}")

    return result


def main():
    print("\n" + "="*60)
    print("SMC 回测系统测试")
    print("="*60)

    try:
        # 测试 1: 数据加载
        df = test_data_loading()

        # 测试 2: SMC 指标计算
        result_df = test_smc_indicators(df)

        # 测试 3: 回测功能
        backtest_result = test_backtest()

        print("\n" + "="*60)
        print("✅ 所有测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()