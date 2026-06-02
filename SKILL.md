---
name: quantcell-backtest
description: |
  QuantCell 策略回测技能。将所有非 NautilusTrader 格式的策略转写为 Python，在本地运行回测。
  
  使用场景:
  - 用户提到 Pine Script 策略需要转写为 Python 回测
  - 用户提到 SMC (Smart Money Concepts) 策略
  - 用户需要回测加密货币 (BTC/ETH/BNB/SOL) 在 1m/15m/1h 周期
  - 用户提到 QuantCell 项目或量化回测
  - 用户需要生成独立 HTML 报告 (回测报告 + 交易记录)
  - 用户提到本地 Parquet 数据或 JasonleeQAQ/multi-asset-ohlcv
  - 用户有 TradingView/MT4/MT5 等格式策略需要转写
  
  当用户说"回测"、"backtest"、"SMC"、"Smart Money"、"Pine Script 转 Python"、
  "加密货币策略"、"QuantCell"、"策略转写"时立即激活此技能。
---

# QuantCell 策略回测技能

## 核心任务

将所有非 NautilusTrader 格式的策略转写为 Python，为每个策略生成独立的 HTML 回测报告。

## 架构决策 (已确定)

| 决策项 | 选择 |
|--------|------|
| 策略迁移 | 所有非 NautilusTrader 格式 → Python |
| 数据+回测 | 只用历史数据，不用实盘 |
| 回测引擎 | 向量化引擎 |
| 数据源 | JasonleeQAQ/multi-asset-ohlcv (Parquet) |
| 币种 | BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT |
| 周期 | 1h, 15m |
| 数据范围 | 2017-08 ~ 2026-01 |

## 性能优化

| 优化项 | 效果 |
|--------|------|
| 向量化引擎 | ~500K bars/sec |
| 全量回测 | 10 策略 × 8 组合 ≈ 2 分钟 |

## 数据配置

数据路径: `/home/da/桌面/multi-asset-ohlcv/cloud_bundle/`

数据来源: https://github.com/JasonleeQAQ/multi-asset-ohlcv (git lfs)

## 手续费配置

| 类型 | 费率 |
|------|------|
| Taker (吃单) | 0.05% |
| Maker (挂单) | 0.02% |

## 初始资金

**1000U**

## HTML 报告功能

每个策略生成独立的 HTML 文件，包含:
- 回测汇总统计
- 权益曲线图
- 完整交易记录 (可筛选/搜索)
- 交易记录包含:
  - 初始资金 (1000U)
  - 入场/出场时间 (UTC+0)
  - 对应价格
  - 手续费 (入/出场)
  - 操作逻辑
  - 净收益/收益率

## 项目结构

```
smc_backtest/
├── strategies/          # 策略模块
├── data/               # 数据加载
│   ├── parquet_loader.py
│   └── duckdb_loader.py
├── engine/             # 回测引擎
│   ├── backtest_engine_v3.py   # 标准回测引擎
│   ├── vector_engine.py        # 向量化引擎
│   ├── individual_report.py   # HTML 报告生成
│   └── parallel_runner.py     # 并行回测
├── reports/            # 生成的报告 (*.html)
├── run_batch_backtest.py      # 批量回测 (推荐)
└── run_optimized_backtest.py  # 单策略全量回测
```

## 快速开始

```bash
cd smc_backtest

# 批量回测 (10 策略 × 8 组合 ≈ 2 分钟)
uv run python run_batch_backtest.py

# 查看报告
open reports/*.html
```

## 硬件建议

| 配置 | 4核6GB (当前) | 8核16GB (推荐) |
|------|--------------|-----------------|
| 10 策略全量 | ~2 分钟 | ~1 分钟 |

## 注意事项

- 不用 Docker
- 不用滚动窗口回测
- 不用蒙特卡洛模拟
- LLM 测试: MiniMax → 文档 → 用户求助
