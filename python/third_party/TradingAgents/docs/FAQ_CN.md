# A股支持常见问题解答 (FAQ)

本文档解答使用 TradingAgents A股功能时的常见问题。

## 📑 目录

- [安装相关](#安装相关)
- [使用相关](#使用相关)
- [数据相关](#数据相关)
- [交易规则](#交易规则)
- [错误处理](#错误处理)
- [性能优化](#性能优化)

---

## 安装相关

### Q1: 如何安装 AKShare？

**A**: 使用 pip 或 uv 安装:

```bash
# 使用 pip
pip install akshare

# 使用 uv (推荐)
uv pip install akshare
```

如果遇到依赖问题，尝试升级 pip:
```bash
pip install --upgrade pip
pip install akshare
```

---

### Q2: AKShare 安装失败怎么办？

**A**: 常见原因和解决方案:

1. **依赖冲突**
   ```bash
   # 创建新的虚拟环境
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或 venv\Scripts\activate  # Windows
   pip install akshare
   ```

2. **网络问题**
   ```bash
   # 使用国内镜像源
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare
   ```

3. **Python 版本**
   - AKShare 需要 Python 3.7+
   - 推荐使用 Python 3.9 或 3.10

---

### Q3: 需要安装哪些其他依赖？

**A**: 完整依赖列表:

```bash
# 核心依赖
pip install akshare
pip install pandas numpy

# TradingAgents 依赖
pip install langchain langchain-core langchain-openai
pip install beautifulsoup4 lxml

# 可选依赖
pip install matplotlib  # 数据可视化
pip install jupyter     # Jupyter Notebook支持
```

---

## 使用相关

### Q4: 如何知道股票代码是否正确？

**A**: A股股票代码规则:

| 交易所 | 代码范围 | 示例 |
|--------|---------|------|
| 上海主板 (SSE) | 600xxx, 601xxx, 603xxx | 600519 (茅台) |
| 科创板 (STAR) | 688xxx | 688981 (中芯) |
| 深圳主板 (SZSE) | 000xxx | 000001 (平安银行) |
| 中小板 (SME) | 002xxx | 002594 (比亚迪) |
| 创业板 (GEM) | 300xxx | 300750 (宁德时代) |
| 北交所 (BSE) | 8xxxxx | 873527 |

验证代码:
```python
def is_valid_a_share(ticker):
    return (
        ticker.isdigit() and
        len(ticker) == 6 and
        ticker[0] in ['0', '3', '6', '8']
    )
```

---

### Q5: 系统如何自动检测A股和美股？

**A**: 系统通过票代码格式自动检测:

```python
# A股检测逻辑
if ticker.isdigit() and len(ticker) == 6:
    # 使用 AKShare 数据源
    use_a_share_tools()
else:
    # 使用 Finnhub/Yahoo Finance 数据源
    use_us_stock_tools()
```

**示例**:
- `600519` → 自动识别为 A股
- `NVDA` → 自动识别为美股

---

### Q6: 在线模式和离线模式有什么区别？

**A**: 两种模式对比:

| 特性 | 在线模式 | 离线模式 |
|------|---------|---------|
| **数据来源** | 实时 API | 缓存数据 |
| **需要网络** | 是 | 否 |
| **数据新鲜度** | 最新 | 可能过时 |
| **速度** | 较慢 | 较快 |
| **适用场景** | 实时分析 | 历史回测 |

**配置方式**:
```python
# 在线模式
config["online_tools"] = True

# 离线模式
config["online_tools"] = False
```

---

## 数据相关

### Q7: AKShare 数据有延迟吗？

**A**: 是的，AKShare 数据可能有延迟:

- **实时行情**: 延迟 3-15 分钟
- **财务数据**: 通常次日更新
- **新闻公告**: 延迟 几分钟到几小时

**不适合**:
- 高频交易
- 秒级决策
- 毫秒级套利

**适合**:
- 日内交易分析
- 中长期投资研究
- 基本面分析

---

### Q8: 可以获取哪些类型的数据？

**A**: TradingAgents A股支持以下数据:

**财务数据**:
- 资产负债表
- 利润表
- 现金流量表
- 财务指标

**市场数据**:
- 实时行情
- 历史K线
- 技术指标

**新闻情绪**:
- 东方财富新闻
- 公司公告
- 股吧讨论

**内部交易**:
- 大宗交易
- 主要股东交易
- 董监高变动

---

### Q9: 如何处理数据缺失？

**A**: 数据缺失处理策略:

```python
try:
    _, decision = ta.propagate("600519", "2024-05-10")
except Exception as e:
    if "No data" in str(e):
        print("数据缺失，可能原因:")
        print("1. 股票在该日期未上市")
        print("2. 停牌")
        print("3. 非交易日")
        print("4. API限制")
```

**建议**:
1. 验证股票代码
2. 检查日期是否为交易日
3. 查看股票历史（上市时间、停牌记录）
4. 联系 AKShare 社区

---

## 交易规则

### Q10: T+1 限制如何工作？

**A**: T+1 是A股特有的交易制度:

**规则**:
- 当日(T日)买入的股票
- 最早在 T+1 日才能卖出
- 不能当日买入当日卖出

**示例**:
```python
buy_date = datetime(2024, 5, 10)   # 星期五买入
sell_date = datetime(2024, 5, 13)  # 星期一才能卖出

# 系统会自动验证
rules = AShareTradingRules()
is_allowed, msg = rules.check_t_plus_1_restriction(
    ticker, buy_date, sell_date
)
```

**注意**: 周末和节假日不是交易日

---

### Q11: 涨跌停板如何计算？

**A**: 不同股票类型有不同的涨跌停限制:

| 股票类型 | 涨跌幅限制 | 示例 |
|---------|-----------|------|
| 普通股 | ±10% | 600519 |
| ST股 | ±5% | ST东方 |
| 科创板 | ±20% | 688xxx |
| 创业板 | ±20% | 300xxx |

**计算公式**:
```python
# 涨停价 = 前收盘价 × (1 + 涨跌幅比例)
# 跌停价 = 前收盘价 × (1 - 涨跌幅比例)

# 示例: 普通股，前收盘 100元
涨停价 = 100 × 1.10 = 110元
跌停价 = 100 × 0.90 = 90元
```

**使用代码**:
```python
lower, upper = rules.calculate_price_limits("600519", 100.00)
print(f"跌停: {lower}, 涨停: {upper}")
# 输出: 跌停: 90.0, 涨停: 110.0
```

---

### Q12: 最小交易单位是多少？

**A**: A股最小交易单位是 **1手 = 100股**

**规则**:
- 买入: 必须是 100股的整数倍
- 卖出: 可以有零股（历史遗留），但新买入必须整手

**验证**:
```python
# 有效交易
rules.validate_trade_size(100)   # ✓ 1手
rules.validate_trade_size(200)   # ✓ 2手
rules.validate_trade_size(1000)  # ✓ 10手

# 无效交易
rules.validate_trade_size(50)    # ✗ 少于1手
rules.validate_trade_size(150)   # ✗ 非100整数倍
```

---

## 错误处理

### Q13: 遇到 "Module not found: akshare" 错误？

**A**: 解决步骤:

1. **检查安装**:
   ```bash
   pip list | grep akshare
   ```

2. **重新安装**:
   ```bash
   pip uninstall akshare
   pip install akshare
   ```

3. **检查环境**:
   ```python
   import sys
   print(sys.path)
   ```

4. **验证导入**:
   ```python
   import akshare as ak
   print(ak.__version__)
   ```

---

### Q14: API 调用失败怎么办？

**A**: 常见原因和解决方案:

**1. 网络问题**
```python
# 增加超时时间
import akshare as ak
ak.stock_zh_a_hist(
    symbol="600519",
    adjust="qfq",
    timeout=30  # 30秒超时
)
```

**2. API 限流**
```python
import time

# 添加延迟
for ticker in tickers:
    analyze(ticker)
    time.sleep(1)  # 等待1秒
```

**3. 数据不存在**
```python
try:
    data = ak.stock_zh_a_hist(symbol="600519")
    if data.empty:
        print("数据为空")
except Exception as e:
    print(f"获取失败: {e}")
```

---

### Q15: 如何调试分析过程？

**A**: 启用调试模式:

```python
# 方法1: 启用 debug 模式
ta = TradingAgentsGraph(debug=True, config=config)

# 方法2: 查看详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 方法3: 检查中间结果
messages, decision = ta.propagate("600519", "2024-05-10")

for msg in messages:
    if hasattr(msg, 'name'):
        print(f"\n=== {msg.name} ===")
        print(msg.content)
```

---

## 性能优化

### Q16: 如何加快分析速度？

**A**: 优化策略:

**1. 使用离线模式**
```python
config["online_tools"] = False  # 使用缓存数据
```

**2. 批量处理**
```python
# 不好: 逐个分析
for ticker in tickers:
    _, decision = ta.propagate(ticker, date)

# 好: 批量分析 (如果支持)
results = ta.batch_analyze(tickers, date)
```

**3. 缓存结果**
```python
import functools

@functools.lru_cache(maxsize=100)
def cached_analyze(ticker, date):
    return ta.propagate(ticker, date)
```

**4. 并发处理**
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(ta.propagate, ticker, date)
        for ticker in tickers
    ]
    results = [f.result() for f in futures]
```

---

### Q17: 内存占用太大怎么办？

**A**: 内存优化技巧:

**1. 限制历史数据范围**
```python
# 只获取最近30天
start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
```

**2. 清理无用数据**
```python
import gc

for ticker in tickers:
    analyze(ticker)
    gc.collect()  # 强制垃圾回收
```

**3. 使用生成器**
```python
def analyze_generator(tickers):
    for ticker in tickers:
        yield ta.propagate(ticker, date)

# 逐个处理，不占用大量内存
for result in analyze_generator(tickers):
    process(result)
```

---

### Q18: 可以并行分析多只股票吗？

**A**: 可以，但需注意:

**线程池方式** (推荐):
```python
from concurrent.futures import ThreadPoolExecutor

def analyze_stock(ticker):
    return ta.propagate(ticker, "2024-05-10")

tickers = ["600519", "000001", "300750"]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(analyze_stock, tickers))
```

**注意事项**:
1. 控制并发数（建议≤5）
2. 注意 API 限流
3. 处理异常情况

---

## 其他问题

### Q19: 支持港股吗？

**A**: 目前**有限支持**

- ✅ 可以通过 AKShare 获取港股数据
- ✅ 股票代码格式: 5位数字（如 00700）
- ⚠️ 交易规则不同（T+0，无涨跌停）
- ⚠️ 需要单独配置

**未来计划**: 完整的港股支持正在开发中

---

### Q20: 如何贡献代码或报告问题？

**A**: 欢迎贡献！

**报告问题**:
1. 访问 [GitHub Issues](https://github.com/ValueCell-ai/valuecell/issues)
2. 描述问题（包含错误信息、复现步骤）
3. 提供环境信息（Python版本、依赖版本）

**贡献代码**:
1. Fork 项目
2. 创建功能分支
3. 提交 Pull Request
4. 等待 Review

**联系方式**:
- GitHub: [ValueCell-ai/valuecell](https://github.com/ValueCell-ai/valuecell)
- 文档: [A_SHARE_SUPPORT.md](../A_SHARE_SUPPORT.md)

---

## 📚 更多资源

- [快速入门指南](QUICKSTART_CN.md)
- [完整文档](../A_SHARE_SUPPORT.md)
- [测试结果](../TEST_RESULTS.md)
- [代码示例](../examples/)
- [AKShare 文档](https://akshare.akfamily.xyz/)

---

**最后更新**: 2025-10-22

如有其他问题，欢迎提交 Issue 或查阅文档！
