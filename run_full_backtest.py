"""
完整回测 + HTML 报告生成

运行全量数据回测并生成包含回测报告和交易日志的 HTML 文件

使用方法:
    uv run python run_full_backtest.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

sys.path.insert(0, str(Path(__file__).parent))

from data import ParquetDataLoader
from strategies import SMCConfig, run_smc_backtest
from engine import save_html_report, export_trades_to_csv, export_results_to_json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_full_backtest():
    """运行完整回测"""
    print("\n" + "="*80)
    print("SMC Strategy 全量回测")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据范围: 2017-08 ~ 2026-01 (全量)")
    print(f"币种: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT")
    print(f"周期: 1m, 15m, 1h")
    print("="*80 + "\n")

    # 配置
    config = SMCConfig()
    config.entry_threshold = 65
    config.require_factors = 3

    # 数据加载器
    loader = ParquetDataLoader()

    # 回测配置
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    intervals = ['1m', '15m', '1h']
    initial_cash = 10000.0

    # 存储结果
    results = {}
    all_trades = []

    # 时间范围
    start_date = '2017-08-01'
    end_date = '2026-01-31'

    # 逐个运行回测
    total_tasks = len(symbols) * len(intervals)
    completed = 0

    for symbol in symbols:
        for interval in intervals:
            completed += 1
            key = f"{symbol}_{interval}"
            
            print(f"\n[{completed}/{total_tasks}] 正在回测: {symbol} {interval}")
            print("-" * 60)

            try:
                # 获取数据文件列表以估计大小
                files = loader.list_available_files(symbol, interval)
                if not files:
                    print(f"  ⚠️ 未找到数据文件，跳过")
                    continue

                # 加载数据
                print(f"  📂 加载数据中... (约 {len(files)} 个月)")
                df = loader.load_single(symbol, interval, start=start_date, end=end_date)
                print(f"  ✅ 加载 {len(df):,} 条 K 线")
                print(f"     时间范围: {df.index[0]} ~ {df.index[-1]}")

                # 运行回测
                print(f"  🔄 运行回测中...")
                result = run_smc_backtest(
                    df,
                    config=config,
                    initial_cash=initial_cash,
                    commission=0.0005,
                    risk_pct=2.0
                )

                # 计算收益率
                total_return = (result.final_cash - result.initial_cash) / result.initial_cash * 100

                # 输出结果
                print(f"  📊 回测结果:")
                print(f"     交易次数: {result.total_trades}")
                print(f"     盈利交易: {result.winning_trades} ({result.win_rate*100:.1f}%)")
                print(f"     亏损交易: {result.losing_trades}")
                print(f"     盈亏比: {result.profit_factor:.2f}")
                print(f"     最大回撤: {result.max_drawdown*100:.1f}%")
                print(f"     总收益: {total_return:.2f}%")
                print(f"     最终资金: ${result.final_cash:,.2f}")

                # 保存结果
                results[key] = result

            except Exception as e:
                print(f"  ❌ 回测失败: {e}")
                import traceback
                traceback.print_exc()

    # 汇总结果
    print("\n" + "="*80)
    print("回测完成! 汇总结果")
    print("="*80)

    # 计算总计
    total_trades = sum(r.total_trades for r in results.values())
    total_wins = sum(r.winning_trades for r in results.values())
    total_pnl = sum(r.total_pnl for r in results.values())
    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

    print(f"\n总体统计:")
    print(f"  总交易次数: {total_trades:,}")
    print(f"  盈利交易: {total_wins} ({overall_wr:.1f}%)")
    print(f"  亏损交易: {total_trades - total_wins}")
    print(f"  总收益: ${total_pnl:,.2f}")
    print(f"  测试组合: {len(results)}/12")

    # 打印表格
    print("\n详细结果:")
    print(f"{'币种':<12} {'周期':<6} {'交易':<8} {'胜率':<8} {'盈亏比':<8} {'最大回撤':<10} {'收益':<12} {'最终资金':<15}")
    print("-" * 100)

    for key in sorted(results.keys()):
        result = results[key]
        symbol = key.split('_')[0]
        interval = key.split('_')[1]
        total_return = (result.final_cash - result.initial_cash) / result.initial_cash * 100

        print(f"{symbol:<12} {interval:<6} {result.total_trades:<8} {result.win_rate*100:<8.1f} {result.profit_factor:<8.2f} {result.max_drawdown*100:<10.1f} {total_return:<12.2f} ${result.final_cash:<15,.2f}")

    # 生成 HTML 报告
    print("\n" + "="*80)
    print("生成 HTML 报告")
    print("="*80)

    output_dir = Path(__file__).parent

    # 保存 HTML
    html_path = output_dir / "smc_backtest_report.html"
    save_html_report(results, config, str(html_path))

    # 导出 CSV
    csv_path = output_dir / "trades.csv"
    export_trades_to_csv(results, str(csv_path))

    # 导出 JSON
    json_path = output_dir / "results.json"
    export_results_to_json(results, str(json_path))

    print("\n" + "="*80)
    print("全部完成!")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print(f"\n📄 输出文件:")
    print(f"   HTML 报告: {html_path}")
    print(f"   交易记录: {csv_path}")
    print(f"   结果数据: {json_path}")

    return results


if __name__ == '__main__':
    run_full_backtest()