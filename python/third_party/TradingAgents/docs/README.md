# TradingAgents A股支持文档中心

欢迎使用 TradingAgents A股支持！本文档中心提供完整的使用指南、示例代码和参考资料。

## 📚 文档导航

### 🚀 新手入门

- **[快速入门指南](QUICKSTART_CN.md)** ⭐ 推荐首先阅读
  - 5分钟快速上手
  - 基础示例代码
  - 常用股票代码
  - 实用技巧

### 💡 深入学习

- **[完整功能文档](../A_SHARE_SUPPORT.md)**
  - 功能详细说明
  - 架构设计
  - API 参考
  - 安装指南

- **[常见问题 FAQ](FAQ_CN.md)**
  - 20+ 常见问题解答
  - 安装问题排查
  - 使用技巧
  - 性能优化

- **[数据源对比](DATA_SOURCES_CN.md)**
  - A股 vs 美股数据源
  - 质量与成本分析
  - 选择建议

### 🧪 测试与示例

- **[测试结果报告](../TEST_RESULTS.md)**
  - 42个测试用例
  - 100% 通过率
  - 功能验证

- **[代码示例](../examples/)**
  - [示例1: 基础A股分析](../examples/example_01_basic_a_share.py)
  - [示例2: 交易规则验证](../examples/example_02_trading_rules.py)
  - [示例3: 批量组合分析](../examples/example_03_portfolio_analysis.py)

---

## 📖 使用流程

### 第一次使用？

```
1. 阅读【快速入门指南】→ 了解基本用法
2. 查看【代码示例】→ 运行示例代码
3. 遇到问题？查看【FAQ】→ 找到解决方案
4. 深入学习？阅读【完整功能文档】→ 掌握所有特性
```

### 已经熟悉基础？

```
1. 查阅【数据源对比】→ 选择最合适的数据源
2. 参考【API 文档】→ 集成到你的项目
3. 查看【测试结果】→ 了解功能边界
4. 阅读【最佳实践】→ 优化使用方式
```

---

## 🎯 快速链接

### 常见任务

| 任务 | 文档链接 |
|------|---------|
| 安装 AKShare | [快速入门 - 安装](QUICKSTART_CN.md#安装) |
| 分析单只A股 | [示例1](../examples/example_01_basic_a_share.py) |
| 验证交易规则 | [示例2](../examples/example_02_trading_rules.py) |
| 批量分析组合 | [示例3](../examples/example_03_portfolio_analysis.py) |
| 计算涨跌停 | [FAQ Q11](FAQ_CN.md#q11-涨跌停板如何计算) |
| 处理T+1限制 | [FAQ Q10](FAQ_CN.md#q10-t1-限制如何工作) |
| 选择数据源 | [数据源对比](DATA_SOURCES_CN.md) |

### 常见问题

| 问题 | 解答链接 |
|------|---------|
| AKShare安装失败？ | [FAQ Q2](FAQ_CN.md#q2-akshare-安装失败怎么办) |
| 如何判断股票代码？ | [FAQ Q4](FAQ_CN.md#q4-如何知道股票代码是否正确) |
| 数据有延迟吗？ | [FAQ Q7](FAQ_CN.md#q7-akshare-数据有延迟吗) |
| 如何优化速度？ | [FAQ Q16](FAQ_CN.md#q16-如何加快分析速度) |
| 支持港股吗？ | [FAQ Q19](FAQ_CN.md#q19-支持港股吗) |

---

## 🔧 技术参考

### 支持的交易所

| 交易所 | 代码格式 | 示例 | 文档 |
|-------|---------|------|------|
| 上交所 (SSE) | 6xxxxx | 600519 | [快速入门](QUICKSTART_CN.md#常用股票代码) |
| 科创板 (STAR) | 688xxx | 688981 | [快速入门](QUICKSTART_CN.md#常用股票代码) |
| 深交所 (SZSE) | 000xxx, 002xxx | 000001 | [快速入门](QUICKSTART_CN.md#常用股票代码) |
| 创业板 (GEM) | 300xxx | 300750 | [快速入门](QUICKSTART_CN.md#常用股票代码) |
| 北交所 (BSE) | 8xxxxx | 873527 | [完整文档](../A_SHARE_SUPPORT.md) |

### A股特有规则

| 规则 | 说明 | 文档 |
|------|------|------|
| T+1交易 | 当日买入次日卖出 | [FAQ Q10](FAQ_CN.md#q10-t1-限制如何工作) |
| 涨跌停板 | ±10% / ±5% / ±20% | [FAQ Q11](FAQ_CN.md#q11-涨跌停板如何计算) |
| 最小手数 | 100股（1手） | [FAQ Q12](FAQ_CN.md#q12-最小交易单位是多少) |

---

## 📊 功能特性

### ✅ 已实现

- [x] 自动市场检测（A股/美股）
- [x] 多交易所支持（SSE/SZSE/GEM/STAR/BSE）
- [x] 完整交易规则验证
- [x] AKShare 数据集成
- [x] 中文新闻和情绪分析
- [x] 财务报表分析
- [x] 大宗交易数据

### 🚧 开发中

- [ ] 港股完整支持
- [ ] 实时行情推送
- [ ] 高级中文NLP
- [ ] 北向资金流向
- [ ] 融资融券数据

---

## 🤝 贡献与反馈

### 报告问题

如果遇到问题，请：

1. 查看 [FAQ](FAQ_CN.md) 是否已有解答
2. 查看 [测试结果](../TEST_RESULTS.md) 了解已知限制
3. 提交 [GitHub Issue](https://github.com/ValueCell-ai/valuecell/issues)

### 贡献文档

欢迎改进文档！

1. Fork 项目
2. 编辑文档
3. 提交 Pull Request

### 联系方式

- **GitHub**: [ValueCell-ai/valuecell](https://github.com/ValueCell-ai/valuecell)
- **Issues**: [反馈问题](https://github.com/ValueCell-ai/valuecell/issues)

---

## 📝 文档列表

### 核心文档

1. **[QUICKSTART_CN.md](QUICKSTART_CN.md)** - 快速入门指南
2. **[FAQ_CN.md](FAQ_CN.md)** - 常见问题解答
3. **[DATA_SOURCES_CN.md](DATA_SOURCES_CN.md)** - 数据源对比
4. **[A_SHARE_SUPPORT.md](../A_SHARE_SUPPORT.md)** - 完整功能文档
5. **[TEST_RESULTS.md](../TEST_RESULTS.md)** - 测试结果报告

### 示例代码

1. **[example_01_basic_a_share.py](../examples/example_01_basic_a_share.py)**
2. **[example_02_trading_rules.py](../examples/example_02_trading_rules.py)**
3. **[example_03_portfolio_analysis.py](../examples/example_03_portfolio_analysis.py)**

### 测试文件

1. **[test_a_share_support.py](../test_a_share_support.py)**
2. **[test_trading_rules_standalone.py](../test_trading_rules_standalone.py)**

---

## 🎓 学习路径

### 初级 (1-2小时)

1. ✅ 阅读快速入门指南
2. ✅ 运行示例1: 基础A股分析
3. ✅ 了解交易规则基础

### 中级 (3-5小时)

1. ✅ 阅读完整功能文档
2. ✅ 运行示例2: 交易规则验证
3. ✅ 了解数据源差异
4. ✅ 尝试批量分析

### 高级 (1-2天)

1. ✅ 研究代码实现
2. ✅ 自定义分析策略
3. ✅ 优化性能
4. ✅ 贡献代码或文档

---

## 📈 版本历史

- **v1.0.0** (2025-10-22)
  - ✅ 初始版本发布
  - ✅ 完整A股支持
  - ✅ 全套文档
  - ✅ 3个示例代码
  - ✅ 100% 测试通过

---

## ⚖️ 免责声明

本工具仅供学习研究使用，不构成投资建议。投资有风险，入市需谨慎。

使用本工具进行的任何投资决策及其后果，由使用者自行承担。

---

**最后更新**: 2025-10-22
**维护者**: ValueCell Team
**许可证**: 与 ValueCell 项目相同

---

[⬆️ 返回顶部](#tradingagents-a股支持文档中心)
