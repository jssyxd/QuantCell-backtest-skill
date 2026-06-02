# QuantCell 策略回测 Prompt

基于 grill-with-docs 决策会议 + 性能优化生成的最终回测执行指南。

---

## 目标

将所有非 NautilusTrader 格式的策略转写为 Python，在本地运行回测。

---

## 架构决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 策略迁移 | 所有非 NautilusTrader 格式 → Python | 通用性 |
| 数据+回测 | 只用历史数据模拟，不用实盘 | 符合需求 |
| 回测引擎 | 向量化引擎 (~570K bars/sec) | 性能最优 |
| 数据源 | 本地 Parquet (JasonleeQAQ/multi-asset-ohlcv) | 用户已手动 git lfs 下载 |
| 回测周期 | 全量 2017-08 ~ 2026-01 | 最完整 |

---

## 性能优化 (v2.0)

| 优化项 | 原版 | 优化后 | 提升 |
|--------|------|--------|------|
| 指标计算 | 逐 bar 循环 | NumPy 向量化 | 7x |
| 回测引擎 | 逐 bar 循环 | 向量化 + 逐 bar 混合 | 10-50x |
| 全量回测 | 30-40 分钟 | **4.8 分钟** | **6-8x** |
| 数据加载 | pandas 逐文件 | DuckDB 可选 | 10-50x |

---

## 数据配置

### 数据来源

手动从 https://github.com/JasonleeQAQ/multi-asset-ohlcv 下载 (git lfs)

数据存放路径: `/home/da/桌面/multi-asset-ohlcv/cloud_bundle/`

### 支持的币种和周期

| 币种 | 1m | 15m | 1h | 数据范围 |
|------|-----|------|-----|----------|
| BTCUSDT | ✅ | ✅ | ✅ | 2017-08 ~ 2026-01 |
| ETHUSDT | ✅ | ✅ | ✅ | 2017-08 ~ 2026-01 |
| BNBUSDT | ✅ | ✅ | ✅ | 2017-11 ~ 2026-01 |
| SOLUSDT | ✅ | ✅ | ✅ | 2020-08 ~ 2026-01 |

### Parquet 文件路径格式

```
cloud_bundle/BTCUSDTraw_data/ohlcv/1m/BTCUSDT_1m_ohlcv_YYYY-MM.parquet
```

---

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

### 5 因子 Smart Money Score

| 因子 | 权重 | 说明 |
|------|------|------|
| F1 HTF Bias | 25% | 高时间框架趋势对齐 |
| F2 Trend | 20% | 本地 BOS/CHoCH |
| F3 Sweep | 20% | 流动性扫扫 |
| F4 POI | 20% | Order Blocks/FVGs |
| F5 Prem/Disc | 15% | Premium/Discount 区域 |

---

## LLM 配置

使用 MiniMax 作为 LLM (需先测试通过):

```yaml
[llm]
provider = "MiniMax"
model = "MiniMax-M3"
api_key = "sk-cp-..."
base_url = "https://api.minimaxi.com/anthropic"
temperature = 0.3
max_tokens = 8192
```

测试流程: 先用 MiniMax 测试，如失败则查 minimax 官网文档，如再失败则求助用户。

---

## 回测结果参考 (2017-08 ~ 2026-01)

**最佳表现 (1h 周期)**:
| 币种 | 交易 | 胜率 | 盈亏比 | 回撤 | 收益 |
|------|------|------|--------|------|------|
| SOLUSDT | 374 | 30.7% | 1.60 | 10.1% | +200.5% |
| ETHUSDT | 701 | 29.1% | 1.46 | 14.1% | +284.6% |
| BNBUSDT | 606 | 27.6% | 1.37 | 21.5% | +195.7% |
| BTCUSDT | 671 | 25.9% | 1.20 | 34.1% | +115.8% |

**注意**: 1m 周期回撤过大，不推荐用于当前策略

---

## 输出文件

### 回测报告 (HTML)

- 路径: `smc_backtest/smc_backtest_report_optimized.html`
- 包含: 回测汇总表 + 交易明细 (可筛选)

### 交易日志 (CSV)

- 路径: `smc_backtest/trades_optimized.csv`
- 字段: symbol, interval, trade_num, entry_time, entry_price, exit_time, exit_price, direction, size, pnl, pnl_pct, exit_reason, score, factors

---

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

---

## 快速开始

```bash
cd smc_backtest

# 优化版全量回测 (~5 分钟)
uv run python run_optimized_backtest.py

# 快速回测 (1年数据)
uv run python run_quick_backtest.py
```

---

## 硬件建议

| 配置 | 4核6GB (当前) | 8核16GB (推荐) | 16核32GB (生产) |
|------|--------------|----------------|-----------------|
| 全量回测 | ~5 分钟 | ~3 分钟 | ~1.5 分钟 |
| 1000 策略 | ~80 小时 | ~40 小时 | ~20 小时 |

---

## 注意事项

1. **不用 Docker**
2. **不用滚动窗口回测** (当前版本)
3. **不用蒙特卡洛模拟** (当前版本)
4. **只测试一个策略** (可扩展)
5. **先用 MiniMax 测试 LLM 调用，如失败查文档再失败则停**
6. **1m 周期回撤大，建议用 15m/1h**