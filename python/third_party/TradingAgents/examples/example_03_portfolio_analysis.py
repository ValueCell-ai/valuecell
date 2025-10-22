#!/usr/bin/env python3
"""
示例 3: A股投资组合批量分析

这个示例展示如何批量分析多只 A股，构建投资组合。
"""

import sys
sys.path.insert(0, '/home/user/valuecell/python/third_party/TradingAgents')

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from datetime import datetime

print("="*80)
print("示例 3: A股投资组合批量分析")
print("="*80)
print()

# ============================================================================
# 定义投资组合
# ============================================================================
print("定义投资组合...")
print("-"*80)

portfolio = {
    "白酒": [
        ("600519", "贵州茅台"),
        ("000858", "五粮液"),
    ],
    "银行": [
        ("600036", "招商银行"),
        ("000001", "平安银行"),
    ],
    "新能源": [
        ("300750", "宁德时代"),
        ("002594", "比亚迪"),
    ],
    "科技": [
        ("688981", "中芯国际"),
        ("300059", "东方财富"),
    ],
}

total_stocks = sum(len(stocks) for stocks in portfolio.values())
print(f"✓ 投资组合定义完成")
print(f"  - 行业数量: {len(portfolio)}")
print(f"  - 股票数量: {total_stocks}")

for sector, stocks in portfolio.items():
    print(f"  - {sector}: {len(stocks)}只")

print()

# ============================================================================
# 配置分析参数
# ============================================================================
print("配置分析参数...")
print("-"*80)

config = DEFAULT_CONFIG.copy()
config["online_tools"] = False  # 使用离线模式进行演示

trade_date = "2024-05-10"

print(f"✓ 分析日期: {trade_date}")
print(f"✓ 数据模式: {'在线' if config['online_tools'] else '离线'}")
print()

# ============================================================================
# 初始化 TradingAgents
# ============================================================================
print("初始化 TradingAgents...")
print("-"*80)

try:
    ta = TradingAgentsGraph(debug=False, config=config)
    print("✓ 初始化成功")
except Exception as e:
    print(f"✗ 初始化失败: {e}")
    print("\n提示: 由于依赖限制，此示例可能无法在所有环境运行")
    print("这是一个概念性示例，展示如何组织批量分析代码")
    sys.exit(0)

print()

# ============================================================================
# 批量分析函数
# ============================================================================

def analyze_portfolio(ta, portfolio, trade_date):
    """批量分析投资组合"""

    results = {}

    for sector, stocks in portfolio.items():
        print(f"\n分析 {sector} 板块...")
        print("-"*60)

        sector_results = {}

        for ticker, name in stocks:
            print(f"  分析 {name} ({ticker})...", end=" ")

            try:
                _, decision = ta.propagate(ticker, trade_date)
                sector_results[ticker] = {
                    "name": name,
                    "decision": decision,
                    "status": "成功"
                }
                print("✓")

            except Exception as e:
                sector_results[ticker] = {
                    "name": name,
                    "decision": None,
                    "status": "失败",
                    "error": str(e)
                }
                print(f"✗ ({str(e)[:30]}...)")

        results[sector] = sector_results

    return results


# ============================================================================
# 生成投资组合报告
# ============================================================================

def generate_portfolio_report(results):
    """生成投资组合分析报告"""

    print("\n" + "="*80)
    print("投资组合分析报告")
    print("="*80)
    print()

    # 统计信息
    total_analyzed = 0
    total_success = 0
    total_failed = 0

    recommendations = {
        "BUY": [],
        "HOLD": [],
        "SELL": [],
        "UNKNOWN": []
    }

    for sector, sector_results in results.items():
        print(f"\n【{sector}板块】")
        print("-"*60)

        for ticker, result in sector_results.items():
            total_analyzed += 1
            name = result['name']

            if result['status'] == "成功":
                total_success += 1
                decision = result['decision']

                # 简单的决策解析（实际需要更复杂的逻辑）
                if decision and isinstance(decision, str):
                    if 'BUY' in decision.upper():
                        rec = "BUY"
                    elif 'SELL' in decision.upper():
                        rec = "SELL"
                    elif 'HOLD' in decision.upper():
                        rec = "HOLD"
                    else:
                        rec = "UNKNOWN"
                else:
                    rec = "UNKNOWN"

                recommendations[rec].append((ticker, name))

                print(f"  {ticker} {name:12s}: 建议 {rec}")
            else:
                total_failed += 1
                print(f"  {ticker} {name:12s}: 分析失败")

    # 汇总统计
    print("\n" + "="*80)
    print("汇总统计")
    print("="*80)
    print(f"总计分析: {total_analyzed}只")
    print(f"成功: {total_success}只")
    print(f"失败: {total_failed}只")
    print()

    print("投资建议分布:")
    for action, stocks in recommendations.items():
        if stocks:
            print(f"  {action:8s}: {len(stocks):2d}只 - {', '.join([s[1] for s in stocks[:3]])}")

    return recommendations


# ============================================================================
# 执行分析（演示模式）
# ============================================================================

print("="*80)
print("开始批量分析")
print("="*80)

# 由于环境限制，这里使用模拟数据演示
print("\n⚠ 演示模式: 使用模拟数据")
print()

# 模拟结果
mock_results = {
    "白酒": {
        "600519": {"name": "贵州茅台", "decision": "HOLD - 估值合理", "status": "成功"},
        "000858": {"name": "五粮液", "decision": "BUY - 价格回调", "status": "成功"},
    },
    "银行": {
        "600036": {"name": "招商银行", "decision": "BUY - 基本面强劲", "status": "成功"},
        "000001": {"name": "平安银行", "decision": "HOLD - 观望", "status": "成功"},
    },
    "新能源": {
        "300750": {"name": "宁德时代", "decision": "BUY - 行业领先", "status": "成功"},
        "002594": {"name": "比亚迪", "decision": "BUY - 销量增长", "status": "成功"},
    },
    "科技": {
        "688981": {"name": "中芯国际", "decision": "HOLD - 等待突破", "status": "成功"},
        "300059": {"name": "东方财富", "decision": "SELL - 技术面弱", "status": "成功"},
    },
}

# 生成报告
generate_portfolio_report(mock_results)

print()
print("="*80)
print("示例完成")
print("="*80)
print()
print("提示: 实际使用时，请配置正确的 API 密钥并使用在线模式")
print("参考 .env.example 文件进行配置")
