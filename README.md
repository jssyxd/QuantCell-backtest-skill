# QuantCell-backtest-skill

SMC (Smart Money Concepts) 策略回测技能。将 TradingView Pine Script 策略转写为 Python，在本地运行回测。

## 功能

- 将 DeFiers-SMC Strategy (Pine Script v6) 转写为 Python
- 支持 BTC/ETH/BNB/SOL 在 1m/15m/1h 周期的回测
- 生成包含回测报告和交易日志的 HTML 文件
- 向量化指标计算 (~83K bars/sec)

## 数据来源

数据来自 [JasonleeQAQ/multi-asset-ohlcv](https://github.com/JasonleeQAQ/multi-asset-ohlcv)，需手动 git lfs 下载到:

```
/home/da/桌面/multi-asset-ohlcv/cloud_bundle/
```

## 快速开始

```bash
cd QuantCell-backtest-skill

# 初始化
uv init --python 3.12
uv add pandas pyarrow polars duckdb numpy

# 运行快速回测 (1年数据)
uv run python run_quick_backtest.py

# 查看报告
open smc_backtest_report.html
```

## 项目结构

```
├── strategies/          # SMC 策略
│   ├── indicators.py    # 向量化指标
│   └── smc_strategy.py  # 回测引擎
├── data/                # 数据加载
│   └── parquet_loader.py
├── engine/              # 报告生成
│   ├── backtest_runner.py
│   └── report_generator.py
├── tests/               # 测试
└── run_*.py             # 回测入口
```

## SMC 策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| entry_threshold | 65 | 最小 Score |
| require_factors | 3 | 最少活跃因子 |
| rr_tp1 | 1.5 | TP1 R:R |
| rr_tp2 | 3.0 | TP2 R:R |
| risk_pct | 2.0% | 每笔风险 |

## 输出文件

- `smc_backtest_report.html` - HTML 回测报告
- `trades.csv` - 交易记录
- `results.json` - 完整数据

## 注意

- 不用 Docker
- 不用滚动窗口回测
- 不用蒙特卡洛模拟
- 只测试 DeFiers-SMC 策略