"""
SMC 回测主程序

使用方法:
    uv run python main.py --symbol BTCUSDT --interval 15m
    uv run python main.py --batch
"""

import argparse
import logging
import sys
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_single_test(symbol: str, interval: str):
    """运行单个测试"""
    from engine import BacktestRunner

    runner = BacktestRunner()

    try:
        result, data = runner.run_single(
            symbol=symbol,
            interval=interval,
            initial_cash=10000.0
        )

        print("\n" + "="*60)
        print("回测完成!")
        print("="*60)
        print(f"总交易次数: {result.total_trades}")
        print(f"盈利交易: {result.winning_trades}")
        print(f"亏损交易: {result.losing_trades}")
        print(f"胜率: {result.win_rate * 100:.2f}%")
        print(f"盈亏比: {result.profit_factor:.2f}")
        print(f"最大回撤: {result.max_drawdown * 100:.2f}%")
        print(f"总收益: {(result.final_cash - result.initial_cash) / result.initial_cash * 100:.2f}%")

        # 显示前 5 笔交易
        if result.trades:
            print("\n前 5 笔交易:")
            for i, trade in enumerate(result.trades[:5]):
                print(f"  {i+1}. {trade.direction.name} @ {trade.entry_price:.2f} -> {trade.exit_price:.2f if trade.exit_price else 'N/A'} | PnL: {trade.pnl:.2f} | 原因: {trade.exit_reason}")

    except Exception as e:
        logger.error(f"回测失败: {e}")
        import traceback
        traceback.print_exc()


def run_batch_test():
    """运行批量测试"""
    from engine import BacktestRunner

    runner = BacktestRunner()

    try:
        # 测试 4 个币种 x 3 个周期
        results = runner.run_batch(
            symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
            intervals=["1m", "15m", "1h"],
            initial_cash=10000.0
        )

        runner.print_summary()

    except Exception as e:
        logger.error(f"批量回测失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description='SMC 回测工具')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='币种')
    parser.add_argument('--interval', type=str, default='15m', help='周期')
    parser.add_argument('--batch', action='store_true', help='运行批量测试')
    parser.add_argument('--debug', action='store_true', help='调试模式')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.batch:
        run_batch_test()
    else:
        run_single_test(args.symbol, args.interval)


if __name__ == '__main__':
    main()