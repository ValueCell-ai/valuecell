# A股支持快速入门指南

> 5分钟快速上手 TradingAgents A股分析功能

## 📚 目录

- [安装](#安装)
- [基础使用](#基础使用)
- [高级功能](#高级功能)
- [常用股票代码](#常用股票代码)
- [下一步](#下一步)

---

## 🚀 安装

### 1. 安装依赖

```bash
# 使用 pip
pip install akshare

# 或使用 uv (推荐)
uv pip install akshare
```

### 2. 验证安装

```python
import akshare as ak
print(f"AKShare 版本: {ak.__version__}")
```

预期输出：
```
AKShare 版本: 1.x.x
```

---

## 💡 基础使用

### 示例 1: 分析单只A股

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 配置
config = DEFAULT_CONFIG.copy()
config["online_tools"] = True  # 使用在线数据

# 初始化
ta = TradingAgentsGraph(debug=True, config=config)

# 分析贵州茅台
ticker = "600519"  # 贵州茅台
date = "2024-05-10"

messages, decision = ta.propagate(ticker, date)

# 查看交易决策
print(decision)
```

**输出示例**:
```
Based on comprehensive analysis:
- Fundamentals: Strong balance sheet, consistent revenue growth
- News: Positive sentiment from recent earnings
- Social Media: High engagement on Guba (股吧)
- Technical: RSI indicates oversold condition

RECOMMENDATION: BUY
Confidence: 85%
```

### 示例 2: 对比A股和美股

```python
# A股分析（自动检测）
a_share_ticker = "600519"  # 茅台
_, a_share_decision = ta.propagate(a_share_ticker, "2024-05-10")

# 美股分析（自动检测）
us_ticker = "NVDA"  # 英伟达
_, us_decision = ta.propagate(us_ticker, "2024-05-10")

print("A股分析:", a_share_decision)
print("美股分析:", us_decision)
```

### 示例 3: 批量分析A股

```python
# A股组合
a_share_portfolio = [
    "600519",  # 贵州茅台
    "600036",  # 招商银行
    "300750",  # 宁德时代
    "000858",  # 五粮液
]

results = {}
for ticker in a_share_portfolio:
    _, decision = ta.propagate(ticker, "2024-05-10")
    results[ticker] = decision

# 打印结果
for ticker, decision in results.items():
    print(f"{ticker}: {decision}")
```

---

## 🔧 高级功能

### 1. 自定义分析日期

```python
from datetime import datetime, timedelta

# 分析历史数据
past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
_, decision = ta.propagate("600519", past_date)
```

### 2. 使用离线模式（回测）

```python
config = DEFAULT_CONFIG.copy()
config["online_tools"] = False  # 使用缓存数据

ta = TradingAgentsGraph(config=config)
_, decision = ta.propagate("600519", "2024-01-10")
```

### 3. 验证交易规则

```python
from tradingagents.agents.risk_mgmt.a_share_trading_rules import AShareTradingRules

rules = AShareTradingRules()

# 检查涨跌停
ticker = "600519"
prev_close = 1800.00
lower, upper = rules.calculate_price_limits(ticker, prev_close)
print(f"涨停价: ¥{upper}, 跌停价: ¥{lower}")

# 验证交易
assessment = rules.generate_risk_assessment(
    ticker="600519",
    trade_action="BUY",
    trade_price=1850.00,
    trade_shares=200,
    prev_close=1800.00,
    company_name="贵州茅台"
)

if assessment["passed"]:
    print("✓ 交易通过风险检查")
else:
    print("✗ 交易被阻止:")
    for issue in assessment["issues"]:
        print(f"  - {issue}")
```

### 4. 获取详细分析报告

```python
# 启用调试模式查看完整分析过程
ta = TradingAgentsGraph(debug=True, config=config)

messages, decision = ta.propagate("600519", "2024-05-10")

# messages 包含所有分析师的详细报告
for msg in messages:
    if hasattr(msg, 'name'):
        print(f"\n=== {msg.name} ===")
        print(msg.content[:500])  # 前500字符
```

---

## 📊 常用股票代码

### 上海证券交易所 (SSE)

| 代码 | 公司名称 | 行业 |
|------|---------|------|
| 600519 | 贵州茅台 | 白酒 |
| 600036 | 招商银行 | 银行 |
| 600276 | 恒瑞医药 | 医药 |
| 601318 | 中国平安 | 保险 |
| 600887 | 伊利股份 | 食品 |

### 深圳证券交易所 (SZSE)

| 代码 | 公司名称 | 行业 |
|------|---------|------|
| 000001 | 平安银行 | 银行 |
| 000002 | 万科A | 地产 |
| 000858 | 五粮液 | 白酒 |
| 002594 | 比亚迪 | 新能源汽车 |

### 创业板 (GEM)

| 代码 | 公司名称 | 行业 |
|------|---------|------|
| 300750 | 宁德时代 | 电池 |
| 300059 | 东方财富 | 金融科技 |
| 300015 | 爱尔眼科 | 医疗服务 |

### 科创板 (STAR)

| 代码 | 公司名称 | 行业 |
|------|---------|------|
| 688981 | 中芯国际 | 芯片制造 |
| 688599 | 天合光能 | 光伏 |
| 688111 | 金山办公 | 软件 |

---

## 🎯 实用技巧

### 技巧 1: 快速判断股票类型

```python
def get_stock_info(ticker):
    """快速获取股票信息"""
    if ticker.startswith('6'):
        exchange = "上海证券交易所 (SSE)"
        if ticker.startswith('688'):
            board = "科创板 (STAR)"
        else:
            board = "主板"
    elif ticker.startswith('00'):
        exchange = "深圳证券交易所 (SZSE)"
        if ticker.startswith('002'):
            board = "中小板 (SME)"
        else:
            board = "主板"
    elif ticker.startswith('3'):
        exchange = "深圳证券交易所 (SZSE)"
        board = "创业板 (GEM)"
    elif ticker.startswith('8'):
        exchange = "北京证券交易所 (BSE)"
        board = "主板"
    else:
        return "未知股票"

    return f"{exchange} - {board}"

# 使用
print(get_stock_info("600519"))  # 上海证券交易所 (SSE) - 主板
print(get_stock_info("300750"))  # 深圳证券交易所 (SZSE) - 创业板 (GEM)
```

### 技巧 2: 交易前风险检查清单

```python
def pre_trade_check(ticker, price, shares, prev_close):
    """交易前检查清单"""
    rules = AShareTradingRules()

    print(f"交易前检查: {ticker}")
    print("-" * 50)

    # 1. 市场类型
    market = rules.get_market_type(ticker)
    print(f"✓ 市场类型: {market}")

    # 2. 涨跌停
    lower, upper = rules.calculate_price_limits(ticker, prev_close)
    print(f"✓ 涨跌停范围: ¥{lower} - ¥{upper}")

    # 3. 手数
    is_valid, msg = rules.validate_trade_size(shares)
    if is_valid:
        print(f"✓ 手数验证: 通过 ({shares}股 = {shares//100}手)")
    else:
        print(f"✗ 手数验证: {msg}")

    # 4. 价格
    is_valid, msg = rules.validate_trade_price(ticker, price, prev_close)
    if is_valid:
        print(f"✓ 价格验证: 通过")
    else:
        print(f"✗ 价格验证: {msg}")

    print("-" * 50)

# 使用
pre_trade_check("600519", 1850.00, 200, 1800.00)
```

### 技巧 3: 数据源选择

```python
# 在线模式 - 实时数据
config_online = DEFAULT_CONFIG.copy()
config_online["online_tools"] = True
ta_online = TradingAgentsGraph(config=config_online)

# 离线模式 - 历史回测
config_offline = DEFAULT_CONFIG.copy()
config_offline["online_tools"] = False
ta_offline = TradingAgentsGraph(config=config_offline)

# 实时分析用在线模式
_, realtime = ta_online.propagate("600519", "2024-05-10")

# 回测用离线模式
_, backtest = ta_offline.propagate("600519", "2024-01-10")
```

---

## 📖 下一步

### 深入学习

1. **完整文档**: 阅读 [A_SHARE_SUPPORT.md](../A_SHARE_SUPPORT.md)
2. **测试结果**: 查看 [TEST_RESULTS.md](../TEST_RESULTS.md)
3. **代码示例**: 运行 [examples/](../examples/) 目录下的示例

### 实践项目

1. **构建A股监控系统**: 监控自选股，自动分析
2. **回测策略**: 使用历史数据验证交易策略
3. **多因子分析**: 结合基本面、技术面、情绪面

### 获取帮助

- **问题反馈**: [GitHub Issues](https://github.com/ValueCell-ai/valuecell/issues)
- **文档**: [ValueCell 文档](https://github.com/ValueCell-ai/valuecell)
- **AKShare文档**: [AKShare 官方文档](https://akshare.akfamily.xyz/)

---

## ⚠️ 重要提示

1. **数据延迟**: AKShare数据可能有延迟，不建议用于高频交易
2. **风险提示**: 本工具仅供学习研究，投资有风险，入市需谨慎
3. **API限制**: 请合理使用数据接口，避免频繁请求
4. **T+1规则**: 系统会自动验证T+1限制，当日买入次日才能卖出

---

## 📝 快速参考

### 命令速查

```python
# 初始化
ta = TradingAgentsGraph(debug=True, config={"online_tools": True})

# 分析A股
_, decision = ta.propagate("600519", "2024-05-10")

# 检查交易规则
rules = AShareTradingRules()
lower, upper = rules.calculate_price_limits(ticker, prev_close)

# 验证交易
assessment = rules.generate_risk_assessment(...)
```

### 常见股票代码

- 茅台: 600519
- 招行: 600036
- 平安: 000001
- 比亚迪: 002594
- 宁德时代: 300750
- 中芯国际: 688981

---

**快速入门指南** | [返回顶部](#a股支持快速入门指南) | [完整文档](../A_SHARE_SUPPORT.md)
