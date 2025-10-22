#!/usr/bin/env python3
"""
示例 1: A股基础分析

这个示例展示如何使用 TradingAgents 分析单只 A股。
"""

import sys
sys.path.insert(0, '/home/user/valuecell/python/third_party/TradingAgents')

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

print("="*80)
print("示例 1: A股基础分析 - 贵州茅台 (600519)")
print("="*80)
print()

# ============================================================================
# 步骤 1: 配置
# ============================================================================
print("步骤 1: 配置 TradingAgents")
print("-"*80)

config = DEFAULT_CONFIG.copy()
config["online_tools"] = True  # 使用在线数据源

print("✓ 配置完成")
print(f"  - 在线模式: {config['online_tools']}")
print()

# ============================================================================
# 步骤 2: 初始化
# ============================================================================
print("步骤 2: 初始化 TradingAgentsGraph")
print("-"*80)

try:
    ta = TradingAgentsGraph(debug=True, config=config)
    print("✓ TradingAgents 初始化成功")
except Exception as e:
    print(f"✗ 初始化失败: {e}")
    print("\n提示: 请确保安装了所有依赖:")
    print("  pip install langchain langchain-core langchain-openai")
    sys.exit(1)

print()

# ============================================================================
# 步骤 3: 分析股票
# ============================================================================
print("步骤 3: 分析贵州茅台")
print("-"*80)

ticker = "600519"  # 贵州茅台
trade_date = "2024-05-10"

print(f"股票代码: {ticker}")
print(f"分析日期: {trade_date}")
print()

# 注意: 实际使用时需要配置 API 密钥
print("提示: 此示例需要配置以下环境变量:")
print("  - OPENAI_API_KEY 或 OPENROUTER_API_KEY")
print("  - 参考 .env.example 文件配置")
print()

try:
    print("开始分析 (这可能需要几分钟)...")
    messages, decision = ta.propagate(ticker, trade_date)

    print("\n" + "="*80)
    print("分析完成！")
    print("="*80)
    print()

    # 显示决策
    print("交易决策:")
    print("-"*80)
    print(decision)
    print()

    # 显示分析师报告摘要
    print("分析师报告摘要:")
    print("-"*80)

    analyst_names = []
    for msg in messages:
        if hasattr(msg, 'name') and 'analyst' in msg.name.lower():
            analyst_names.append(msg.name)

    if analyst_names:
        print(f"✓ 参与分析的分析师: {', '.join(set(analyst_names))}")

    print()

except Exception as e:
    print(f"\n✗ 分析失败: {e}")
    print("\n可能的原因:")
    print("  1. 未配置 API 密钥")
    print("  2. 网络连接问题")
    print("  3. API 配额不足")
    print("\n建议:")
    print("  - 检查 .env 文件配置")
    print("  - 验证 API 密钥有效性")

print()
print("="*80)
print("示例完成")
print("="*80)
