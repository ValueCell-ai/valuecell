# 数据源对比：A股 vs 美股

本文档详细对比 TradingAgents 在分析 A股和美股时使用的不同数据源。

## 📑 目录

- [数据源总览](#数据源总览)
- [详细对比](#详细对比)
- [数据质量](#数据质量)
- [成本分析](#成本分析)
- [使用建议](#使用建议)

---

## 数据源总览

### A股数据源

| 数据类型 | 主要数据源 | 备选数据源 |
|---------|-----------|-----------|
| **实时行情** | AKShare | - |
| **历史K线** | AKShare | - |
| **财务报表** | AKShare (东方财富) | - |
| **新闻资讯** | AKShare (东方财富) | Google News |
| **公司公告** | AKShare | - |
| **社交情绪** | 东方财富股吧 | - |
| **内部交易** | AKShare (大宗交易) | - |

### 美股数据源

| 数据类型 | 主要数据源 | 备选数据源 |
|---------|-----------|-----------|
| **实时行情** | Yahoo Finance | Finnhub |
| **历史K线** | Yahoo Finance | - |
| **财务报表** | SimFin | Finnhub |
| **新闻资讯** | Finnhub | OpenAI |
| **SEC文件** | Finnhub | - |
| **社交情绪** | Reddit | Twitter |
| **内部交易** | Finnhub (SEC) | - |

---

## 详细对比

### 1. 基本面分析数据

#### A股（AKShare）

**优势**:
- ✅ 数据来源：东方财富、新浪财经等权威源
- ✅ 中文数据，无需翻译
- ✅ 完全免费
- ✅ 覆盖全面（SSE、SZSE、BSE等）

**劣势**:
- ⚠️ 数据延迟（通常15分钟）
- ⚠️ API稳定性一般
- ⚠️ 文档主要为中文

**数据示例**:
```python
import akshare as ak

# 获取资产负债表
df = ak.stock_balance_sheet_by_report_em(symbol="600519")

# 可用字段
# - TOTAL_ASSETS (总资产)
# - TOTAL_LIABILITIES (总负债)
# - TOTAL_EQUITY (股东权益)
# - MONETARY_CAP (货币资金)
# ...
```

#### 美股（SimFin + Finnhub）

**优势**:
- ✅ 数据来源：SEC官方文件
- ✅ 数据标准化
- ✅ API稳定
- ✅ 英文文档完善

**劣势**:
- ⚠️ SimFin 免费版限制较多
- ⚠️ Finnhub 需要 API Key
- ⚠️ 部分高级数据需付费

**数据示例**:
```python
# SimFin 资产负债表
# 字段标准化：
# - Total Assets
# - Total Liabilities
# - Total Equity
# - Cash & Cash Equivalents
```

---

### 2. 新闻数据

#### A股（东方财富 + Google News）

**数据源**:
- 东方财富新闻 API
- 新浪财经
- Google News（中文）

**特点**:
- ✅ 新闻丰富，更新及时
- ✅ 本地化内容
- ✅ 包含政策新闻
- ⚠️ 需要中文NLP处理

**示例**:
```python
# 获取公司新闻
df_news = ak.stock_news_em(symbol="600519")

# 返回字段：
# - 新闻标题
# - 发布时间
# - 新闻内容
# - 来源
```

#### 美股（Finnhub + OpenAI）

**数据源**:
- Finnhub Company News
- Google News（英文）
- OpenAI News API（付费）

**特点**:
- ✅ 全球新闻覆盖
- ✅ API 稳定
- ✅ 支持情绪分析
- ⚠️ 需要 API Key

---

### 3. 社交情绪数据

#### A股（股吧）

**数据源**: 东方财富股吧

**特点**:
- ✅ 中国最大的股票论坛
- ✅ 反映散户情绪
- ✅ 实时讨论
- ⚠️ 噪音较多
- ⚠️ 需要爬虫或API

**指标**:
- 帖子数量
- 阅读量
- 评论数
- 热度排名

**代码示例**:
```python
# 获取股吧数据
df_guba = ak.stock_guba_em(symbol="600519")

# 分析指标：
# - 阅读量 → 关注度
# - 评论数 → 活跃度
# - 发帖时间 → 时间分布
```

#### 美股（Reddit）

**数据源**: Reddit (r/wallstreetbets, r/stocks等)

**特点**:
- ✅ 全球最大的股票讨论社区
- ✅ API 成熟
- ✅ 情绪分析工具丰富
- ⚠️ 以散户为主

**指标**:
- 提及次数
- 上下投票比
- 评论情绪
- 趋势变化

---

### 4. 内部交易/大宗交易

#### A股（大宗交易数据）

**数据类型**:
- 大宗交易
- 主要股东减持
- 董监高交易

**特点**:
- ✅ 信息披露较规范
- ✅ 数据可通过AKShare获取
- ⚠️ 与美国内部交易概念不同

**示例**:
```python
# 大宗交易数据
df = ak.stock_em_dxjy_xx(symbol="600519")

# 字段：
# - 股东名称
# - 变动方向（增持/减持）
# - 变动股本
# - 成交均价
# - 持股比例
```

#### 美股（SEC Insider Trading）

**数据类型**:
- Form 4 (内部交易报告)
- Insider Sentiment

**特点**:
- ✅ SEC强制披露
- ✅ 数据准确性高
- ✅ Finnhub提供API

**示例**:
```python
# Finnhub Insider Trading
# 包括：
# - Transaction Date
# - Transaction Type (Buy/Sell)
# - Shares
# - Transaction Price
# - Insider Name & Position
```

---

## 数据质量对比

### 准确性

| 维度 | A股 (AKShare) | 美股 (Finnhub/SimFin) |
|------|--------------|---------------------|
| **财务数据** | ⭐⭐⭐⭐ (来自官方) | ⭐⭐⭐⭐⭐ (SEC官方) |
| **行情数据** | ⭐⭐⭐⭐ (延迟15分钟) | ⭐⭐⭐⭐⭐ (实时可选) |
| **新闻数据** | ⭐⭐⭐⭐ (本地源可靠) | ⭐⭐⭐⭐ (全球覆盖) |
| **情绪数据** | ⭐⭐⭐ (噪音较多) | ⭐⭐⭐⭐ (工具成熟) |

### 覆盖范围

| 市场 | 股票数量 | 数据历史 | 更新频率 |
|------|---------|---------|---------|
| **A股** | ~5000只 | ~10年 | 每日/实时 |
| **美股** | ~8000只 | ~20年 | 每日/实时 |

### 延迟情况

| 数据类型 | A股延迟 | 美股延迟 |
|---------|--------|---------|
| **实时行情** | 15分钟 | 0-15分钟 (取决于提供商) |
| **财务报表** | 1-2天 | 同日 (盘后) |
| **新闻** | 几分钟-几小时 | 实时-几分钟 |
| **公告** | 几分钟 | 实时 |

---

## 成本分析

### A股数据成本

| 服务 | 成本 | 限制 |
|------|------|-----|
| **AKShare** | 免费 | 无官方API限制，但建议合理使用 |
| **东方财富** | 免费 | 网页爬虫，请勿过度请求 |
| **Google News** | 免费 | 标准配额 |

**总结**: **完全免费** ✅

### 美股数据成本

| 服务 | 免费额度 | 付费计划 |
|------|---------|---------|
| **Finnhub** | 60 calls/min | $0-399/月 |
| **Yahoo Finance** | 免费（非官方） | - |
| **SimFin** | 有限 | $14-99/月 |
| **OpenAI API** | - | 按使用计费 |

**总结**: **部分免费，高级功能需付费** ⚠️

---

## 使用建议

### 选择A股数据源的场景

✅ **推荐使用A股数据源**:
1. 分析中国公司
2. 需要中文新闻和公告
3. 关注政策影响
4. 预算有限（免费）
5. 研究散户情绪

### 选择美股数据源的场景

✅ **推荐使用美股数据源**:
1. 分析美国公司
2. 需要全球新闻覆盖
3. 要求数据标准化
4. 需要SEC官方文件
5. 有API预算

### 混合使用建议

对于**跨市场分析**，建议：

```python
def analyze_stock(ticker):
    if is_a_share(ticker):
        # 使用A股数据源
        sources = {
            "fundamentals": "akshare",
            "news": "eastmoney",
            "sentiment": "guba"
        }
    else:
        # 使用美股数据源
        sources = {
            "fundamentals": "simfin",
            "news": "finnhub",
            "sentiment": "reddit"
        }

    return analyze_with_sources(ticker, sources)
```

---

## 数据源API对比

### AKShare API示例

```python
import akshare as ak

# 1. 获取实时行情
df = ak.stock_zh_a_spot_em()

# 2. 获取历史数据
df = ak.stock_zh_a_hist(symbol="600519", period="daily", adjust="qfq")

# 3. 获取财务数据
df = ak.stock_financial_analysis_indicator(symbol="600519")

# 4. 获取新闻
df = ak.stock_news_em(symbol="600519")

# 5. 获取股吧讨论
df = ak.stock_guba_em(symbol="600519")
```

### Finnhub API示例

```python
import finnhub

# 1. 初始化
finnhub_client = finnhub.Client(api_key="YOUR_API_KEY")

# 2. 获取公司资料
profile = finnhub_client.company_profile2(symbol='AAPL')

# 3. 获取新闻
news = finnhub_client.company_news('AAPL', _from="2024-01-01", to="2024-05-01")

# 4. 获取内部交易
insider = finnhub_client.stock_insider_transactions('AAPL')

# 5. 获取财务数据
financials = finnhub_client.financials('AAPL', 'annual')
```

---

## 未来发展

### 计划中的改进

**A股数据源**:
- [ ] 支持更多数据提供商（Tushare、Wind）
- [ ] 增强实时数据支持
- [ ] 改进中文NLP情绪分析
- [ ] 添加北向资金流向数据

**美股数据源**:
- [ ] 整合更多免费数据源
- [ ] 优化API调用成本
- [ ] 支持加密货币市场
- [ ] 增加ESG数据

**跨市场**:
- [ ] 港股完整支持
- [ ] A股-港股-美股联动分析
- [ ] 统一的数据接口标准

---

## 总结

| 维度 | A股(AKShare) | 美股(Finnhub/SimFin) | 优胜方 |
|------|-------------|-------------------|-------|
| **成本** | 免费 | 部分收费 | 🏆 A股 |
| **数据标准化** | 较好 | 优秀 | 🏆 美股 |
| **本地化** | 完美 | 一般 | 🏆 A股 |
| **API稳定性** | 一般 | 优秀 | 🏆 美股 |
| **历史数据** | ~10年 | ~20年 | 🏆 美股 |
| **社区支持** | 活跃(中文) | 活跃(英文) | 平手 |

### 最佳实践

1. **A股投资者**: 主要使用 AKShare，辅以 Google News
2. **美股投资者**: Finnhub (免费额度) + Yahoo Finance
3. **跨市场研究**: 自动检测 + 混合数据源
4. **预算有限**: 优先使用免费数据源
5. **专业机构**: 考虑付费高级数据

---

**相关文档**:
- [快速入门指南](QUICKSTART_CN.md)
- [常见问题FAQ](FAQ_CN.md)
- [A股支持完整文档](../A_SHARE_SUPPORT.md)

**最后更新**: 2025-10-22
