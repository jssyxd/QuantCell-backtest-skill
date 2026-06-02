---
name: quantcell-backtest
description: |
  QuantCell 策略回测技能。将所有非 NautilusTrader 格式的策略转写为 Python，在本地运行回测。
  
  使用场景:
  - 用户提到 Pine Script 策略需要转写为 Python 回测
  - 用户提到 SMC (Smart Money Concepts) 策略
  - 用户需要回测加密货币 (BTC/ETH/BNB/SOL) 在 1m/15m/1h 周期
  - 用户提到 QuantCell 项目或量化回测
  - 用户需要生成 HTML 回测报告
  - 用户提到本地 Parquet 数据或 JasonleeQAQ/multi-asset-ohlcv
  - 用户有 TradingView/MT4/MT5 等格式策略需要转写
  - 用户有自定义策略格式需要适配
  
  当用户说"回测"、"backtest"、"SMC"、"Smart Money"、"Pine Script 转 Python"、
  "加密货币策略"、"QuantCell"、"策略转写"、"strategy conversion"时立即激活此技能。
  
  支持的策略格式: Pine Script, MQL4/MQL5, TradingView, 财经公式, 自定义 Python/JS 等
  转写目标: Python 向量化策略 + 本地回测引擎
---

# QuantCell 策略回测技能

## 核心任务

将所有非 NautilusTrader 格式的策略转写为 Python，运行本地回测。

## 架构决策 (已确定)

| 决策项 | 选择 |
|--------|------|
| 策略迁移 | 所有非 NautilusTrader 格式 → Python |
| 数据+回测 | 只用历史数据，不用实盘 |
| 回测引擎 | 向量化引擎 (~570K bars/sec) |
| 数据加载 | Parquet (pandas) 或 DuckDB (加速) |
| 数据源 | JasonleeQAQ/multi-asset-ohlcv |
| 币种 | BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT |
| 周期 | 1m, 15m, 1h |
| 数据范围 | 2017-08 ~ 2026-01 |

## 性能优化 (v2.0)

| 优化项 | 效果 |
|--------|------|
| 向量化指标计算 | ~83K → ~570K bars/sec (7x) |
| 向量化回测引擎 | 逐 bar → 向量化 (10-50x) |
| 全量回测耗时 | 30+ 分钟 → **4.8 分钟** |
| DuckDB 数据加载 | 可选，比 pandas 快 10-50x |
| 并行回测 | 可选，多核并行 |

## 数据配置

数据路径: `/home/da/桌面/multi-asset-ohlcv/cloud_bundle/`

数据来源: 手动从 https://github.com/JasonleeQAQ/multi-asset-ohlcv git lfs 下载

Parquet 文件格式:
```
cloud_bundle/BTCUSDTraw_data/ohlcv/1m/BTCUSDT_1m_ohlcv_YYYY-MM.parquet
```

## 策略参数 (优化后)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| entry_threshold | 65 | 最小 Score (0-100) |
| require_factors | 3 | 最少活跃因子 (1-5) |
| swing_len | 10 | 枢轴检测长度 |
| vol_mult | 1.5 | OB 成交量倍数 |
| rr_tp1 | **1.2** | TP1 R:R (优化: 1.5→1.2) |
| rr_tp2 | **2.5** | TP2 R:R (优化: 3.0→2.5) |
| risk_pct | 2.0% | 每笔风险 |
| sl_buffer_atr | 0.5 | 止损 ATR 缓冲 |

## 回测结果参考 (2017-08 ~ 2026-01)

**最佳表现 (1h 周期)**:
| 币种 | 交易 | 胜率 | 盈亏比 | 回撤 | 收益 |
|------|------|------|--------|------|------|
| SOLUSDT | 374 | 30.7% | 1.60 | 10.1% | +200.5% |
| ETHUSDT | 701 | 29.1% | 1.46 | 14.1% | +284.6% |
| BNBUSDT | 606 | 27.6% | 1.37 | 21.5% | +195.7% |
| BTCUSDT | 671 | 25.9% | 1.20 | 34.1% | +115.8% |

**注意**: 1m 周期回撤过大，不推荐用于当前策略

## 输出

1. **HTML 回测报告**: 包含汇总表 + 交易明细 (可筛选)
2. **CSV 交易日志**: 所有交易记录

## 项目结构

```
smc_backtest/
├── strategies/
│   ├── indicators.py      # 向量化指标 (~570K bars/sec)
│   └── smc_strategy.py    # 逐 bar 回测引擎
├── data/
│   ├── parquet_loader.py  # Parquet 加载
│   └── duckdb_loader.py   # DuckDB 加速加载 (可选)
├── engine/
│   ├── vector_engine.py   # 向量化回测引擎 (推荐)
│   ├── parallel_runner.py # 并行回测 (可选)
│   └── report_generator.py
├── run_optimized_backtest.py  # 优化版全量回测 (推荐)
├── run_quick_backtest.py      # 快速回测 (1年)
└── run_full_backtest.py       # 原版全量回测
```

## 快速开始

```bash
cd smc_backtest
uv run python run_optimized_backtest.py
```

## 硬件建议

| 配置 | 4核6GB (当前) | 8核16GB (推荐) | 16核32GB (生产) |
|------|--------------|----------------|-----------------|
| 全量回测 | ~5 分钟 | ~3 分钟 | ~1.5 分钟 |
| 1000 策略 | ~80 小时 | ~40 小时 | ~20 小时 |

## 注意事项

- 不用 Docker
- 不用滚动窗口回测
- 不用蒙特卡洛模拟
- LLM 测试: MiniMax → 文档 → 用户求助
- 1m 周期回撤大，建议用 15m/1h