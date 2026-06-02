# QuantCell SMC 回测 Prompt

基于 grill-with-docs 决策会议生成的最终回测执行指南。

---

## 目标

将 TradingView Pine Script 策略 (DeFiers-SMC Strategy v0.4.0) 转写为 Python，在本地运行回测。

---

## 架构决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 策略迁移 | Pine → Python 完整实现 | 保持功能完整性 |
| 数据+回测 | 只用历史数据模拟，不用实盘 | 符合需求 |
| 回测引擎 | 自研 Python 引擎 (向量化指标) | 性能 ~83K bars/sec |
| 数据源 | 本地 Parquet (JasonleeQAQ/multi-asset-ohlcv) | 用户已手动 git lfs 下载 |
| 回测周期 | 全量 2017-08 ~ 2026-01 | 最完整 |

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
cloud_bundle/
├── BTCUSDTraw_data/ohlcv/
│   ├── 1m/BTCUSDT_1m_ohlcv_YYYY-MM.parquet
│   ├── 15m/BTCUSDT_15m_ohlcv_YYYY-MM.parquet
│   └── 1h/BTCUSDT_1h_ohlcv_YYYY-MM.parquet
├── ETHUSDTraw_data/ohlcv/
└── ...
```

---

## SMC 策略配置

### 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `entry_threshold` | 65 | 最小 Score (0-100) |
| `require_factors` | 3 | 最少活跃因子数 (1-5) |
| `swing_len` | 10 | 枢轴检测长度 |
| `vol_mult` | 1.5 | OB 成交量倍数 |
| `fvg_min_atr` | 0.5 | FVG 最小 ATR |
| `ob_max_age` | 60 | OB 最大年龄 (bars) |
| `liq_range_pct` | 0.15 | 流动性容差 (%) |
| `sl_buffer_atr` | 0.5 | 止损 ATR 缓冲 |
| `rr_tp1` | 1.5 | TP1 R:R |
| `rr_tp2` | 3.0 | TP2 R:R |
| `risk_pct` | 2.0 | 每笔风险 (%) |
| `use_trailing` | True | 启用追踪止损 |
| `use_early_be` | True | 启用提前 Break-Even |

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

## 输出文件

### 回测报告 (HTML)

- 路径: `smc_backtest/smc_backtest_report.html`
- 包含: 回测汇总表 + 交易明细 (可筛选)
- 大小: ~7-10MB

### 交易日志 (CSV)

- 路径: `smc_backtest/trades.csv`
- 字段: symbol, interval, trade_num, entry_time, entry_price, exit_time, exit_price, direction, size, pnl, pnl_pct, exit_reason, score, factors

---

## 项目结构

```
smc_backtest/
├── strategies/
│   ├── indicators.py    # SMC 向量化指标 (NumPy/Pandas)
│   └── smc_strategy.py  # 策略 + 回测引擎
├── data/
│   └── parquet_loader.py  # Parquet 数据加载
├── engine/
│   ├── backtest_runner.py  # 批量回测
│   └── report_generator.py # HTML 报告
├── tests/
│   └── test_smc.py
├── main.py              # 入口
├── run_quick_backtest.py  # 快速回测 (2024-01 ~ 2025-01)
└── run_full_backtest.py   # 完整回测 (2017-08 ~ 2026-01)
```

---

## 快速开始

```bash
cd smc_backtest

# 初始化 (如需要)
uv init --python 3.12
uv add pandas pyarrow polars duckdb numpy

# 运行快速回测 (1年数据)
uv run python run_quick_backtest.py

# 查看报告
open smc_backtest_report.html
```

---

## 注意事项

1. **不用 Docker**
2. **不用滚动窗口回测** (当前版本)
3. **不用蒙特卡洛模拟** (当前版本)
4. **只测试一个策略** (DeFiers-SMC)
5. **先用 MiniMax 测试 LLM 调用，如失败查文档再失败则停**