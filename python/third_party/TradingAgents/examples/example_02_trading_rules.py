#!/usr/bin/env python3
"""
示例 2: A股交易规则验证

这个示例展示如何使用 A股交易规则模块验证交易。
"""

from datetime import datetime, timedelta

print("="*80)
print("示例 2: A股交易规则验证")
print("="*80)
print()

# ============================================================================
# 导入交易规则模块
# ============================================================================
print("导入交易规则模块...")

try:
    import sys
    sys.path.insert(0, '/home/user/valuecell/python/third_party/TradingAgents')
    from tradingagents.agents.risk_mgmt.a_share_trading_rules import AShareTradingRules
    print("✓ 模块导入成功")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("请确保路径正确")
    sys.exit(1)

print()

# 初始化规则引擎
rules = AShareTradingRules()

# ============================================================================
# 示例 1: 识别股票市场类型
# ============================================================================
print("示例 1: 识别股票市场类型")
print("-"*80)

stocks = [
    ("600519", "贵州茅台"),
    ("688981", "中芯国际"),
    ("000001", "平安银行"),
    ("300750", "宁德时代"),
]

for ticker, name in stocks:
    market_type = rules.get_market_type(ticker)
    print(f"  {ticker} ({name:8s}): {market_type}")

print()

# ============================================================================
# 示例 2: 计算涨跌停板
# ============================================================================
print("示例 2: 计算涨跌停板")
print("-"*80)

examples = [
    ("600519", "贵州茅台", 1800.00, "普通股"),
    ("688981", "中芯国际", 50.00, "科创板"),
    ("300750", "宁德时代", 200.00, "创业板"),
    ("600123", "ST东方", 10.00, "ST股"),
]

for ticker, name, prev_close, stock_type in examples:
    lower, upper = rules.calculate_price_limits(
        ticker, prev_close, name
    )
    pct = ((upper - prev_close) / prev_close) * 100

    print(f"\n{name} ({ticker}) - {stock_type}")
    print(f"  前收盘: ¥{prev_close:,.2f}")
    print(f"  跌停价: ¥{lower:,.2f} ({-pct:.1f}%)")
    print(f"  涨停价: ¥{upper:,.2f} (+{pct:.1f}%)")

print()

# ============================================================================
# 示例 3: 验证交易手数
# ============================================================================
print("\n示例 3: 验证交易手数")
print("-"*80)

test_sizes = [50, 100, 150, 200, 500, 1000]

for shares in test_sizes:
    is_valid, msg = rules.validate_trade_size(shares)
    lots = shares // 100

    if is_valid:
        print(f"  ✓ {shares:4d}股 ({lots}手): 有效")
    else:
        print(f"  ✗ {shares:4d}股: {msg}")

print()

# ============================================================================
# 示例 4: 验证交易价格
# ============================================================================
print("示例 4: 验证交易价格")
print("-"*80)

ticker = "600519"
prev_close = 1800.00
lower_limit, upper_limit = rules.calculate_price_limits(ticker, prev_close)

test_prices = [
    1600.00,  # 低于跌停
    1620.00,  # 跌停价
    1700.00,  # 正常范围
    1980.00,  # 涨停价
    2000.00,  # 高于涨停
]

print(f"\n{ticker} 前收盘: ¥{prev_close}, 涨跌停: ¥{lower_limit} - ¥{upper_limit}")
print()

for price in test_prices:
    is_valid, msg = rules.validate_trade_price(ticker, price, prev_close)

    if is_valid:
        if msg:  # 有警告
            print(f"  ⚠ ¥{price:7.2f}: {msg}")
        else:
            print(f"  ✓ ¥{price:7.2f}: 有效")
    else:
        print(f"  ✗ ¥{price:7.2f}: {msg}")

print()

# ============================================================================
# 示例 5: T+1 交易限制
# ============================================================================
print("示例 5: T+1 交易限制")
print("-"*80)

buy_date = datetime(2024, 5, 10, 9, 30)

test_dates = [
    (datetime(2024, 5, 10, 14, 0), "当日下午"),
    (datetime(2024, 5, 11, 10, 0), "次日上午"),
    (datetime(2024, 5, 13, 10, 0), "T+3"),
]

print(f"\n买入日期: {buy_date.strftime('%Y-%m-%d %H:%M')}")
print()

for sell_date, desc in test_dates:
    is_allowed, msg = rules.check_t_plus_1_restriction(
        ticker, buy_date, sell_date
    )

    days = (sell_date - buy_date).days
    sell_str = sell_date.strftime('%Y-%m-%d %H:%M')

    if is_allowed:
        print(f"  ✓ {sell_str} (T+{days}, {desc}): 允许卖出")
    else:
        print(f"  ✗ {sell_str} (T+{days}, {desc}): 禁止卖出")
        print(f"      原因: {msg}")

print()

# ============================================================================
# 示例 6: 完整的交易验证
# ============================================================================
print("示例 6: 完整的交易前验证")
print("-"*80)

def validate_trade(ticker, action, price, shares, prev_close, company_name=""):
    """完整的交易前验证流程"""

    print(f"\n交易验证: {company_name} ({ticker})")
    print(f"  操作: {action}")
    print(f"  价格: ¥{price:,.2f}")
    print(f"  数量: {shares}股 ({shares//100}手)")
    print(f"  前收盘: ¥{prev_close:,.2f}")
    print()

    assessment = rules.generate_risk_assessment(
        ticker=ticker,
        trade_action=action,
        trade_price=price,
        trade_shares=shares,
        prev_close=prev_close,
        company_name=company_name
    )

    # 显示结果
    print("  验证结果:")
    print(f"    市场类型: {assessment['market_type']}")
    print(f"    是否ST股: {'是' if assessment['is_st_stock'] else '否'}")
    print(f"    涨跌停范围: ¥{assessment['price_limits']['lower']} - ¥{assessment['price_limits']['upper']}")

    if assessment['warnings']:
        print(f"\n  ⚠ 警告:")
        for warning in assessment['warnings']:
            print(f"    - {warning}")

    if assessment['issues']:
        print(f"\n  ✗ 问题:")
        for issue in assessment['issues']:
            print(f"    - {issue}")

    print(f"\n  最终结果: {'✓ 交易允许' if assessment['passed'] else '✗ 交易拒绝'}")

    return assessment['passed']


# 测试用例 1: 正常交易
validate_trade(
    ticker="600519",
    action="BUY",
    price=1850.00,
    shares=200,
    prev_close=1800.00,
    company_name="贵州茅台"
)

# 测试用例 2: 价格超限
validate_trade(
    ticker="600519",
    action="BUY",
    price=2000.00,
    shares=200,
    prev_close=1800.00,
    company_name="贵州茅台"
)

# 测试用例 3: 手数不符
validate_trade(
    ticker="300750",
    action="BUY",
    price=180.00,
    shares=150,  # 非100整数倍
    prev_close=200.00,
    company_name="宁德时代"
)

print()
print("="*80)
print("示例完成")
print("="*80)
