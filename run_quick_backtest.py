"""
快速回测 + HTML 报告生成 (2024-2025 完整年)

运行 1 年数据回测并生成包含回测报告和交易日志的 HTML 文件

使用方法:
    uv run python run_quick_backtest.py
"""

import sys
from pathlib import Path
from datetime import datetime
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


def run_quick_backtest():
    """运行快速回测 (2024 全年)"""
    print("\n" + "="*80)
    print("SMC Strategy 快速回测 (2024-01 ~ 2025-01)")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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

    # 时间范围 (1年)
    start_date = '2024-01-01'
    end_date = '2025-01-31'

    # 存储结果
    results = {}

    # 逐个运行回测
    total_tasks = len(symbols) * len(intervals)
    completed = 0

    for symbol in symbols:
        for interval in intervals:
            completed += 1
            key = f"{symbol}_{interval}"
            
            print(f"\n[{completed}/{total_tasks}] {symbol} {interval}")
            print("-" * 50)

            try:
                # 加载数据
                print(f"  📂 加载数据...")
                df = loader.load_single(symbol, interval, start=start_date, end=end_date)
                print(f"  ✅ {len(df):,} 条 K 线 | {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")

                # 运行回测
                print(f"  🔄 回测中...")
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
                print(f"  📊 {result.total_trades} 交易 | WR={result.win_rate*100:.1f}% | PF={result.profit_factor:.2f} | DD={result.max_drawdown*100:.1f}% | Ret={total_return:.1f}%")

                # 保存结果
                results[key] = result

            except Exception as e:
                print(f"  ❌ 失败: {e}")

    # 汇总结果
    print("\n" + "="*80)
    print("回测完成!")
    print("="*80)

    # 计算总计
    total_trades = sum(r.total_trades for r in results.values())
    total_wins = sum(r.winning_trades for r in results.values())
    total_pnl = sum(r.total_pnl for r in results.values())
    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

    print(f"\n总体: {total_trades:,} 交易 | 胜率 {overall_wr:.1f}% | 总收益 ${total_pnl:,.2f}")

    # 打印表格
    print(f"\n{'币种':<12} {'周期':<6} {'交易':<6} {'胜率':<8} {'盈亏比':<8} {'回撤':<8} {'收益':<10}")
    print("-" * 70)
    for key in sorted(results.keys()):
        result = results[key]
        symbol = key.split('_')[0]
        interval = key.split('_')[1]
        total_return = (result.final_cash - result.initial_cash) / result.initial_cash * 100
        print(f"{symbol:<12} {interval:<6} {result.total_trades:<6} {result.win_rate*100:<8.1f} {result.profit_factor:<8.2f} {result.max_drawdown*100:<8.1f} {total_return:<10.1f}")

    # 生成报告
    print("\n" + "="*80)
    print("生成报告")
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

    print(f"\n📄 输出文件:")
    print(f"   HTML: {html_path}")
    print(f"   CSV:  {csv_path}")
    print(f"   JSON: {json_path}")
    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return results


if __name__ == '__main__':
    run_quick_backtest()