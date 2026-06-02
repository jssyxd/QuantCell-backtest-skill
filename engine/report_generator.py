"""
HTML 报告生成器

生成包含回测报告和交易日志的 HTML 文件
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

from strategies import BacktestResult, Trade, SMCConfig


def generate_html_report(
    results: Dict[str, BacktestResult],
    config: SMCConfig,
    title: str = "SMC Strategy Backtest Report"
) -> str:
    """
    生成完整的 HTML 报告

    Args:
        results: 回测结果字典 {symbol_interval: BacktestResult}
        config: SMC 配置
        title: 报告标题

    Returns:
        str: HTML 内容
    """
    # 生成汇总数据
    summary_data = []
    for key, result in results.items():
        summary_data.append({
            'key': key,
            'symbol': key.split('_')[0],
            'interval': key.split('_')[1],
            'initial_cash': result.initial_cash,
            'final_cash': result.final_cash,
            'total_return': (result.final_cash - result.initial_cash) / result.initial_cash * 100,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate': result.win_rate * 100,
            'profit_factor': result.profit_factor,
            'max_drawdown': result.max_drawdown * 100,
            'sharpe_ratio': result.sharpe_ratio,
            'avg_trade_pnl': sum(t.pnl for t in result.trades) / len(result.trades) if result.trades else 0,
        })

    summary_df = pd.DataFrame(summary_data)

    # 计算总计
    total_trades = sum(r.total_trades for r in results.values())
    total_wins = sum(r.winning_trades for r in results.values())
    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    total_return = sum(r.final_cash - r.initial_cash for r in results.values())

    # 生成 HTML
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #0f1419;
            color: #e7e9ea;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1f25 0%, #2d333b 100%);
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
            border: 1px solid #333;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #fff;
        }}
        .header .subtitle {{
            color: #8b949e;
            font-size: 14px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #161b22;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #30363d;
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .stat-card .label {{
            font-size: 14px;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .positive {{ color: #3fb950; }}
        .negative {{ color: #f85149; }}
        .neutral {{ color: #e7e9ea; }}

        .section {{
            background: #161b22;
            border-radius: 12px;
            border: 1px solid #30363d;
            margin-bottom: 30px;
            overflow: hidden;
        }}
        .section-header {{
            background: #1a1f25;
            padding: 20px 24px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
        }}
        .section-body {{
            padding: 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #1a1f25;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #8b949e;
            border-bottom: 1px solid #30363d;
            position: sticky;
            top: 0;
        }}
        td {{
            padding: 14px 16px;
            border-bottom: 1px solid #21262d;
            font-size: 14px;
        }}
        tr:hover {{
            background: #1a1f25;
        }}
        .trade-long {{ color: #3fb950; }}
        .trade-short {{ color: #f85149; }}
        .trade-win {{ color: #3fb950; }}
        .trade-loss {{ color: #f85149; }}

        .tab-container {{
            display: flex;
            border-bottom: 1px solid #30363d;
            background: #1a1f25;
        }}
        .tab {{
            padding: 16px 24px;
            cursor: pointer;
            border: none;
            background: transparent;
            color: #8b949e;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .tab:hover {{
            color: #e7e9ea;
        }}
        .tab.active {{
            color: #1d9bf0;
            border-bottom: 2px solid #1d9bf0;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}

        .config-section {{
            padding: 24px;
        }}
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }}
        .config-item {{
            background: #0f1419;
            padding: 16px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
        }}
        .config-label {{
            color: #8b949e;
        }}
        .config-value {{
            font-weight: 500;
            color: #e7e9ea;
        }}

        .pagination {{
            display: flex;
            justify-content: center;
            padding: 20px;
            gap: 8px;
        }}
        .page-btn {{
            padding: 8px 16px;
            background: #21262d;
            border: none;
            border-radius: 6px;
            color: #e7e9ea;
            cursor: pointer;
            font-size: 13px;
        }}
        .page-btn:hover {{
            background: #30363d;
        }}
        .page-btn.active {{
            background: #1d9bf0;
            color: #fff;
        }}
        .page-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .search-box {{
            padding: 16px 24px;
            background: #1a1f25;
            border-bottom: 1px solid #30363d;
        }}
        .search-input {{
            width: 100%;
            padding: 12px 16px;
            background: #0f1419;
            border: 1px solid #30363d;
            border-radius: 8px;
            color: #e7e9ea;
            font-size: 14px;
        }}
        .search-input:focus {{
            outline: none;
            border-color: #1d9bf0;
        }}

        .filter-bar {{
            display: flex;
            gap: 12px;
            padding: 16px 24px;
            background: #1a1f25;
            border-bottom: 1px solid #30363d;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 8px 16px;
            background: #21262d;
            border: none;
            border-radius: 20px;
            color: #e7e9ea;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }}
        .filter-btn:hover, .filter-btn.active {{
            background: #1d9bf0;
        }}

        .equity-chart {{
            height: 300px;
            background: #0f1419;
            padding: 20px;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        .badge-long {{ background: rgba(63, 185, 80, 0.2); color: #3fb950; }}
        .badge-short {{ background: rgba(248, 81, 73, 0.2); color: #f85149; }}
        .badge-win {{ background: rgba(63, 185, 80, 0.2); color: #3fb950; }}
        .badge-loss {{ background: rgba(248, 81, 73, 0.2); color: #f85149; }}
        .badge-tp1 {{ background: rgba(210, 153, 34, 0.2); color: #d29922; }}
        .badge-tp2 {{ background: rgba(163, 113, 247, 0.2); color: #a371f7; }}
        .badge-sl {{ background: rgba(248, 81, 73, 0.2); color: #f85149; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">
                生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                数据范围: 2017-08 ~ 2026-01 | 
                策略配置: SMC v0.4.0
            </div>
        </div>

        <!-- Overall Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="value {'positive' if total_return > 0 else 'negative'}">${total_return:,.0f}</div>
                <div class="label">总收益</div>
            </div>
            <div class="stat-card">
                <div class="value neutral">{total_trades:,}</div>
                <div class="label">总交易数</div>
            </div>
            <div class="stat-card">
                <div class="value {'positive' if overall_wr > 40 else 'neutral'}">{overall_wr:.1f}%</div>
                <div class="label">综合胜率</div>
            </div>
            <div class="stat-card">
                <div class="value neutral">{(total_wins / total_trades * 100) if total_trades > 0 else 0:.0f}%</div>
                <div class="label">盈利交易</div>
            </div>
            <div class="stat-card">
                <div class="value neutral">{total_trades - total_wins:,}</div>
                <div class="label">亏损交易</div>
            </div>
            <div class="stat-card">
                <div class="value neutral">12</div>
                <div class="label">测试组合</div>
            </div>
        </div>

        <!-- Summary Table -->
        <div class="section">
            <div class="section-header">
                <span class="section-title">📊 回测汇总 (4币种 × 3周期)</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>币种</th>
                        <th>周期</th>
                        <th>交易数</th>
                        <th>胜率</th>
                        <th>盈亏比</th>
                        <th>最大回撤</th>
                        <th>收益</th>
                        <th>最终资金</th>
                    </tr>
                </thead>
                <tbody>
"""

    # 添加汇总行
    for _, row in summary_df.sort_values(['symbol', 'interval']).iterrows():
        return_class = 'positive' if row['total_return'] > 0 else 'negative'
        dd_class = 'negative' if row['max_drawdown'] > 20 else 'neutral'
        
        html += f"""
                    <tr>
                        <td><strong>{row['symbol']}</strong></td>
                        <td>{row['interval']}</td>
                        <td>{row['total_trades']}</td>
                        <td>{row['win_rate']:.1f}%</td>
                        <td>{row['profit_factor']:.2f}</td>
                        <td class="{dd_class}">{row['max_drawdown']:.1f}%</td>
                        <td class="{return_class}">{row['total_return']:.1f}%</td>
                        <td>${row['final_cash']:,.0f}</td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>

        <!-- Detailed Trades -->
        <div class="section">
            <div class="section-header">
                <span class="section-title">📋 交易明细</span>
            </div>
            
            <div class="tab-container">
                <button class="tab active" onclick="showTab('all')">全部</button>
"""

    # 添加币种标签
    for symbol in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']:
        html += f'<button class="tab" onclick="showTab(\'{symbol}\')">{symbol}</button>\n'

    html += """
            </div>

            <div class="search-box">
                <input type="text" class="search-input" placeholder="搜索交易..." id="searchInput" onkeyup="filterTable()">
            </div>

            <div class="filter-bar">
                <button class="filter-btn active" onclick="filterDirection('all')">全部方向</button>
                <button class="filter-btn" onclick="filterDirection('LONG')">只看买入</button>
                <button class="filter-btn" onclick="filterDirection('SHORT')">只看卖出</button>
                <button class="filter-btn" onclick="filterDirection('WIN')">只看盈利</button>
                <button class="filter-btn" onclick="filterDirection('LOSS')">只看亏损</button>
            </div>

            <div id="tradesContainer">
"""

    # 添加每个币种的交易明细
    for key in sorted(results.keys()):
        result = results[key]
        symbol = key.split('_')[0]
        
        html += f'''
                <div class="tab-content{' active' if symbol == 'BTCUSDT' else ''}" id="tab-{symbol}">
                    <div style="padding: 16px 24px; background: #1a1f25; border-bottom: 1px solid #30363d;">
                        <strong>{key}</strong> — {result.total_trades} 笔交易 | 胜率: {result.win_rate*100:.1f}% | 收益: {(result.final_cash - result.initial_cash) / result.initial_cash * 100:.1f}%
                    </div>
                    <table class="trade-table" data-symbol="{symbol}">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>时间</th>
                                <th>方向</th>
                                <th>入场价格</th>
                                <th>出场价格</th>
                                <th>数量</th>
                                <th>PnL</th>
                                <th>PnL%</th>
                                <th>Score</th>
                                <th>Factors</th>
                                <th>原因</th>
                            </tr>
                        </thead>
                        <tbody>
'''

        for i, trade in enumerate(result.trades):
            badge_type = 'long' if trade.direction.value == 1 else 'short'
            direction_badge = f'<span class="badge badge-{badge_type}">{trade.direction.name}</span>'
            
            pnl_class = 'trade-win' if trade.pnl and trade.pnl > 0 else 'trade-loss'
            pnl_str = f'{trade.pnl:,.2f}' if trade.pnl else '-'
            pnl_pct_str = f'{trade.pnl_pct:.2f}%' if trade.pnl_pct else '-'
            
            reason_badge = ''
            if trade.exit_reason:
                reason_lower = trade.exit_reason.lower()
                if 'tp1' in reason_lower:
                    reason_badge = '<span class="badge badge-tp1">TP1</span>'
                elif 'tp2' in reason_lower:
                    reason_badge = '<span class="badge badge-tp2">TP2</span>'
                elif 'stop' in reason_lower:
                    reason_badge = '<span class="badge badge-sl">止损</span>'
                else:
                    reason_badge = f'<span class="badge">{trade.exit_reason}</span>'

            entry_time = trade.entry_time.strftime('%Y-%m-%d %H:%M') if trade.entry_time else '-'
            exit_time = trade.exit_time.strftime('%Y-%m-%d %H:%M') if trade.exit_time else '-'

            html += f'''
                            <tr data-direction="{trade.direction.name}" data-pnl="{'win' if trade.pnl and trade.pnl > 0 else 'loss'}">
                                <td>{i+1}</td>
                                <td>{entry_time}<br><small style="color:#8b949e">{exit_time}</small></td>
                                <td>{direction_badge}</td>
                                <td>{trade.entry_price:,.2f}</td>
                                <td>{f"{trade.exit_price:,.2f}" if trade.exit_price else "-"}</td>
                                <td>{trade.size:.4f}</td>
                                <td class="{pnl_class}">{pnl_str}</td>
                                <td class="{pnl_class}">{pnl_pct_str}</td>
                                <td>{trade.score:.0f}</td>
                                <td>{trade.factors}/5</td>
                                <td>{reason_badge}</td>
                            </tr>
'''

        html += '''
                        </tbody>
                    </table>
                </div>
'''

    html += """
            </div>
        </div>

        <!-- Strategy Configuration -->
        <div class="section">
            <div class="section-header">
                <span class="section-title">⚙️ 策略配置</span>
            </div>
            <div class="config-section">
                <div class="config-grid">
"""

    # 添加配置项
    config_items = [
        ("入场阈值", f"{config.entry_threshold}"),
        ("最低因子数", f"{config.require_factors}"),
        ("Swing Length", f"{config.swing_len}"),
        ("MSS 位移", f"{config.mss_disp_mult}"),
        ("成交量倍数", f"{config.vol_mult}"),
        ("FVG 最小 ATR", f"{config.fvg_min_atr}"),
        ("OB 最大年龄", f"{config.ob_max_age}"),
        ("流动性容差", f"{config.liq_range_pct}%"),
        ("止损缓冲 ATR", f"{config.sl_buffer_atr}"),
        ("TP1 R:R", f"{config.rr_tp1}"),
        ("TP2 R:R", f"{config.rr_tp2}"),
        ("每笔风险", f"{config.risk_pct}%"),
        ("使用 Trailing", f"{config.use_trailing}"),
        ("使用 Early BE", f"{config.use_early_be}"),
    ]

    for label, value in config_items:
        html += f'''
                    <div class="config-item">
                        <span class="config-label">{label}</span>
                        <span class="config-value">{value}</span>
                    </div>
'''

    html += """
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div style="text-align: center; padding: 30px; color: #8b949e; font-size: 13px;">
            SMC Strategy Backtest Report | Generated by QuantCell
        </div>
    </div>

    <script>
        function showTab(symbol) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
                if (tab.textContent === symbol || (symbol === 'all' && tab.textContent === '全部')) {
                    tab.classList.add('active');
                }
            });
            
            // Show/hide content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            if (symbol === 'all') {
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.add('active');
                });
            } else {
                document.getElementById('tab-' + symbol)?.classList.add('active');
            }
        }

        function filterTable() {
            const searchText = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.trade-table tbody tr').forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchText) ? '' : 'none';
            });
        }

        function filterDirection(direction) {
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.textContent.includes(direction) || (direction === 'all' && btn.textContent === '全部方向')) {
                    btn.classList.add('active');
                }
            });

            document.querySelectorAll('.trade-table tbody tr').forEach(row => {
                if (direction === 'all') {
                    row.style.display = '';
                } else if (direction === 'WIN') {
                    row.style.display = row.dataset.pnl === 'win' ? '' : 'none';
                } else if (direction === 'LOSS') {
                    row.style.display = row.dataset.pnl === 'loss' ? '' : 'none';
                } else {
                    row.style.display = row.dataset.direction === direction ? '' : 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

    return html


def save_html_report(
    results: Dict[str, BacktestResult],
    config: SMCConfig,
    output_path: str = "smc_backtest_report.html"
):
    """保存 HTML 报告到文件"""
    html = generate_html_report(results, config)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 报告已保存: {output_path}")
    return output_path


def export_trades_to_csv(results: Dict[str, BacktestResult], output_path: str = "trades.csv"):
    """导出交易记录到 CSV"""
    rows = []
    
    for key, result in results.items():
        symbol = key.split('_')[0]
        interval = key.split('_')[1]
        
        for i, trade in enumerate(result.trades):
            rows.append({
                'symbol': symbol,
                'interval': interval,
                'trade_num': i + 1,
                'entry_time': trade.entry_time,
                'entry_price': trade.entry_price,
                'exit_time': trade.exit_time,
                'exit_price': trade.exit_price,
                'direction': trade.direction.name,
                'size': trade.size,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'exit_reason': trade.exit_reason,
                'score': trade.score,
                'factors': trade.factors,
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"✅ 交易记录已导出: {output_path}")
    return df


def export_results_to_json(results: Dict[str, BacktestResult], output_path: str = "results.json"):
    """导出结果到 JSON"""
    data = {}
    
    for key, result in results.items():
        data[key] = {
            'initial_cash': result.initial_cash,
            'final_cash': result.final_cash,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'max_drawdown': result.max_drawdown,
            'sharpe_ratio': result.sharpe_ratio,
            'total_pnl': result.total_pnl,
            'trades': [
                {
                    'entry_time': str(t.entry_time),
                    'entry_price': t.entry_price,
                    'exit_time': str(t.exit_time) if t.exit_time else None,
                    'exit_price': t.exit_price,
                    'direction': t.direction.name,
                    'size': t.size,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct,
                    'exit_reason': t.exit_reason,
                    'score': t.score,
                    'factors': t.factors,
                }
                for t in result.trades
            ]
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 结果已导出: {output_path}")
    return data