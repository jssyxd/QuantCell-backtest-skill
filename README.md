# QuantCell-backtest-skill

策略回测技能。将所有非 NautilusTrader 格式的策略转写为 Python，在本地运行回测。

## 功能

- 支持 Pine Script / MQL4/MQL5 / TradingView 等格式策略转写
- 向量化回测引擎 (~570K bars/sec)
- 支持 BTC/ETH/BNB/SOL 在 1m/15m/1h 周期的回测
- 生成包含回测报告和交易日志的 HTML 文件
- 全量回测 (2017-08 ~ 2026-01) 约 5 分钟

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

# 运行优化版全量回测 (~5 分钟)
uv run python run_optimized_backtest.py

# 查看报告
open smc_backtest_report_optimized.html
```

## 性能对比

| 指标 | 原版 (逐 bar) | 优化版 (向量化) | 提升 |
|------|--------------|----------------|------|
| 全量回测 | 30-40 分钟 | **4.8 分钟** | **6-8x** |
| 指标计算 | ~83K bars/sec | ~570K bars/sec | **7x** |

## 回测结果参考 (2017-08 ~ 2026-01)

**最佳表现 (1h 周期)**:
| 币种 | 胜率 | 盈亏比 | 回撤 | 收益 |
|------|------|--------|------|------|
| SOLUSDT | 30.7% | 1.60 | 10.1% | +200.5% |
| ETHUSDT | 29.1% | 1.46 | 14.1% | +284.6% |
| BNBUSDT | 27.6% | 1.37 | 21.5% | +195.7% |
| BTCUSDT | 25.9% | 1.20 | 34.1% | +115.8% |

## 项目结构

```
├── strategies/          # SMC 策略 (向量化)
│   ├── indicators.py    # 核心指标 (~570K bars/sec)
│   └── smc_strategy.py  # 逐 bar 回测引擎
├── data/                # 数据加载
│   ├── parquet_loader.py
│   └── duckdb_loader.py  # DuckDB 加速 (可选)
├── engine/              # 回测引擎
│   ├── vector_engine.py  # 向量化引擎 (推荐)
│   ├── parallel_runner.py # 并行回测 (可选)
│   └── report_generator.py
└── run_*.py             # 回测入口
```

## 注意

- 不用 Docker
- 不用滚动窗口回测
- 不用蒙特卡洛模拟
- 1m 周期回撤大，建议用 15m/1h
