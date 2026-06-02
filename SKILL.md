---
name: quantcell-backtest
description: |
  QuantCell SMC 策略回测技能。将 Pine Script 交易策略转写为 Python，在本地运行回测。
  
  使用场景:
  - 用户提到 Pine Script 策略需要转写为 Python 回测
  - 用户提到 SMC (Smart Money Concepts) 策略
  - 用户需要回测加密货币 (BTC/ETH/BNB/SOL) 在 1m/15m/1h 周期
  - 用户提到 QuantCell 项目或量化回测
  - 用户需要生成 HTML 回测报告
  - 用户提到本地 Parquet 数据或 JasonleeQAQ/multi-asset-ohlcv
  
  当用户说"回测"、"backtest"、"SMC"、"Smart Money"、"Pine Script 转 Python"、
  "加密货币策略"、"QuantCell"时立即激活此技能。
---

# QuantCell SMC 回测技能

## 核心任务

将 TradingView Pine Script 策略 (DeFiers-SMC Strategy v0.4.0) 转写为 Python，在本地运行回测。

## 架构决策 (已确定)

| 决策项 | 选择 |
|--------|------|
| 策略迁移 | Pine → Python 完整实现 |
| 数据+回测 | 只用历史数据，不用实盘 |
| 回测引擎 | 自研向量化引擎 (~83K bars/sec) |
| 数据源 | 本地 Parquet (JasonleeQAQ/multi-asset-ohlcv) |
| 币种 | BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT |
| 周期 | 1m, 15m, 1h |
| 数据范围 | 2017-08 ~ 2026-01 |

## 数据配置

数据路径: `/home/da/桌面/multi-asset-ohlcv/cloud_bundle/`

Parquet 文件格式:
```
cloud_bundle/BTCUSDTraw_data/ohlcv/1m/BTCUSDT_1m_ohlcv_YYYY-MM.parquet
```

## SMC 策略参数

| 参数 | 默认值 |
|------|--------|
| entry_threshold | 65 |
| require_factors | 3 |
| swing_len | 10 |
| vol_mult | 1.5 |
| rr_tp1 | 1.5 |
| rr_tp2 | 3.0 |
| risk_pct | 2.0% |

## 输出

1. **HTML 回测报告**: 包含汇总表 + 交易明细 (可筛选)
2. **CSV 交易日志**: 所有交易记录
3. **JSON 结果数据**: 完整回测数据

## 项目结构

```
smc_backtest/
├── strategies/          # SMC 策略 (向量化)
│   ├── indicators.py    # 核心指标
│   └── smc_strategy.py  # 回测引擎
├── data/                # 数据加载
│   └── parquet_loader.py
├── engine/              # 报告生成
│   ├── backtest_runner.py
│   └── report_generator.py
├── run_quick_backtest.py  # 1年回测
└── run_full_backtest.py   # 全量回测
```

## 快速开始

```bash
cd smc_backtest
uv run python run_quick_backtest.py
```

## 注意事项

- 不用 Docker
- 不用滚动窗口回测
- 不用蒙特卡洛模拟
- 只测试一个策略 (DeFiers-SMC)
- LLM 测试: MiniMax → 文档 → 用户求助