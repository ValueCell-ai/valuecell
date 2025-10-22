# YFinance vs AKShare Adapter 对比分析报告

## 测试概述

**测试日期**: 2025-10-22  
**测试范围**: 23个不同资产标的，涵盖股票、ETF和指数  
**测试函数**: 
- `get_asset_info()` - 获取资产详细信息
- `get_real_time_price()` - 获取实时价格
- `get_historical_prices()` - 获取历史价格数据（最近30天）

---

## 测试结果总结

### 整体成功率对比

| 功能函数 | YFinance | AKShare |
|---------|----------|---------|
| **get_asset_info** | 18/23 (78.3%) | 0/23 (0.0%) |
| **get_real_time_price** | 16/23 (69.6%) | 15/23 (65.2%) |
| **get_historical_prices** | 16/23 (69.6%) | 14/23 (60.9%) |

---

## 详细分析

### 1. get_asset_info（获取资产信息）

#### YFinance 表现：✅ 优秀 (78.3%)
- **成功案例**: 18/23
- **优势**:
  - 能够获取大部分美股、港股、A股的详细信息
  - 返回完整的公司名称、交易所、货币等信息
  - 对NASDAQ、NYSE、AMEX、HKEX、SSE、SZSE等主流交易所支持良好

- **失败案例**:
  - BSE:835368 - 北交所股票（YFinance不支持）
  - BSE:560800 - 北交所ETF（YFinance不支持）
  - 部分指数代码：NASDAQ:IXIC, HKEX:HSI, BSE:899050

#### AKShare 表现：❌ 需要修复 (0.0%)
- **问题原因**: API返回数据格式问题（'data' key错误）
- **影响**: 所有ticker的asset info获取都失败
- **需要修复**: `get_asset_info()` 方法中对AKShare API响应的处理逻辑

---

### 2. get_real_time_price（获取实时价格）

#### YFinance 表现：✅ 良好 (69.6%)
- **成功案例**: 16/23
- **优势**:
  - 美股实时数据准确（AAPL, GORO, JPM等）
  - 港股数据可靠（00700腾讯等）
  - A股数据完整（601398工商银行、002594比亚迪等）
  - 加密货币支持（BTC）

- **失败案例**:
  - BSE:835368, BSE:560800 - 北交所资产
  - NASDAQ:IXIC, NYSE:DJI, AMEX:RUT - 部分指数
  - NYSE:SPY - 个别ETF
  - HKEX:HSI, BSE:899050 - 部分指数

#### AKShare 表现：✅ 良好 (65.2%)
- **成功案例**: 15/23
- **优势**:
  - 美股数据准确（AAPL, GORO, JPM, QQQ, GLD等）
  - 港股数据准确（00700, 03033等）
  - A股数据完整（601398, 002594, 300750等）
  - 北交所数据支持（835368, 899050）

- **失败案例**:
  - CRYPTO:BTC - 不支持加密货币
  - NYSE:SPY - 个别美股ETF
  - SSE:510050 - 上交所ETF
  - 大部分指数ticker

- **注意事项**:
  - AKShare返回的价格数据不包含涨跌幅信息（change和change_percent为None）
  - 时间戳精度略低（整点时间）

---

### 3. get_historical_prices（获取历史价格）

#### YFinance 表现：✅ 良好 (69.6%)
- **成功案例**: 16/23
- **数据点数量**:
  - 美股/加密货币: 22-30个数据点
  - 港股: 20个数据点
  - A股: 16个数据点

- **优势**:
  - 数据完整，包含开高低收、成交量
  - 时间精度高，带时区信息
  - 涨跌幅计算准确

#### AKShare 表现：✅ 中等 (60.9%)
- **成功案例**: 14/23
- **数据点数量**:
  - 美股: 22个数据点
  - 港股: 20个数据点
  - A股: 16个数据点

- **优势**:
  - 数据完整度与YFinance相当
  - 支持北交所历史数据（899050）

- **劣势**:
  - 不支持加密货币历史数据
  - 部分ETF历史数据获取失败（SSE:510050, NYSE:SPY等）
  - 部分指数历史数据不可用

---

## 市场覆盖对比

### 美股市场 (NASDAQ, NYSE, AMEX)

| 资产类型 | YFinance | AKShare |
|---------|----------|---------|
| 股票 (AAPL, GORO, JPM) | ✅ 优秀 | ✅ 良好 |
| ETF (QQQ, GLD, SPY) | ✅ 优秀 | ⚠️ 部分支持 |
| 指数 (IXIC, RUT, DJI) | ❌ 不支持 | ❌ 不支持 |

**结论**: YFinance在美股市场表现更全面

### 港股市场 (HKEX)

| 资产类型 | YFinance | AKShare |
|---------|----------|---------|
| 股票 (00700) | ✅ 优秀 | ✅ 良好 |
| ETF (03033) | ✅ 优秀 | ✅ 良好 |
| 指数 (HSI) | ❌ 不支持 | ❌ 不支持 |

**结论**: 两者表现相当

### A股市场 (SSE, SZSE)

| 资产类型 | YFinance | AKShare |
|---------|----------|---------|
| 股票 (601398, 002594, 300750) | ✅ 优秀 | ✅ 良好 |
| ETF (510050, 159919) | ✅ 优秀 | ⚠️ 部分支持 |
| 指数 (000001, 399001) | ✅ 良好 | ✅ 良好 |

**结论**: YFinance在ETF支持上更好，但数据质量相当

### 北交所市场 (BSE)

| 资产类型 | YFinance | AKShare |
|---------|----------|---------|
| 股票 (835368) | ❌ 不支持 | ✅ 支持 |
| ETF (560800) | ❌ 不支持 | ❌ 不支持 |
| 指数 (899050) | ❌ 不支持 | ✅ 支持 |

**结论**: AKShare是北交所数据的唯一选择

### 加密货币市场

| 资产类型 | YFinance | AKShare |
|---------|----------|---------|
| BTC | ✅ 支持 | ❌ 不支持 |

**结论**: YFinance是加密货币数据的唯一选择

---

## 数据质量对比

### 价格数据精度

**YFinance**:
- 价格精度高（多位小数）
- 包含完整的OHLCV数据
- 带时区的时间戳
- 自动计算涨跌幅

**AKShare**:
- 价格精度中等
- OHLCV数据完整
- 时间戳为本地时间
- ❌ 不提供涨跌幅计算

### 资产信息完整度

**YFinance**:
- 公司全称
- 交易所代码
- 货币信息
- 附加属性（市值、PE等）

**AKShare**:
- ❌ 当前版本API返回格式问题，需要修复

---

## 性能对比

### 响应速度
- **YFinance**: 平均每个ticker 1-2秒
- **AKShare**: 平均每个ticker 0.5-1秒

**结论**: AKShare在国内访问速度更快

### 稳定性
- **YFinance**: 偶尔出现HTTP 404错误
- **AKShare**: 稳定性良好，但部分ticker返回None

---

## 推荐使用策略

### 场景1: 美股为主的应用
**推荐**: **YFinance**
- 理由: 更全面的美股支持，包含ETF和部分指数

### 场景2: A股/港股为主的应用
**推荐**: **YFinance + AKShare 组合**
- YFinance: 主数据源
- AKShare: 北交所数据补充

### 场景3: 需要加密货币数据
**推荐**: **YFinance**
- 理由: 唯一支持加密货币的adapter

### 场景4: 需要实时涨跌幅计算
**推荐**: **YFinance**
- 理由: 自动计算并返回涨跌幅数据

### 场景5: 国内网络环境，需要快速响应
**推荐**: **AKShare**
- 理由: 国内服务器，访问速度更快

---

## 需要改进的问题

### YFinance Adapter
1. ✅ **已修复**: `asset_type_mapping` 属性缺失问题
2. ⚠️ **待改进**: 部分指数ticker转换逻辑（IXIC, DJI, HSI等）
3. ⚠️ **待改进**: AMEX交易所的exchange mapping

### AKShare Adapter
1. ❌ **紧急修复**: `get_asset_info()` API响应处理逻辑
   - 错误: `'data'` key不存在
   - 影响: 所有ticker的资产信息获取失败
2. ⚠️ **待改进**: `get_real_time_price()` 返回数据缺少涨跌幅信息
3. ⚠️ **待改进**: 部分ETF的实时价格和历史价格获取失败

---

## 结论

### 综合评分

| 维度 | YFinance | AKShare |
|-----|----------|---------|
| **市场覆盖广度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **数据完整性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **数据准确性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **响应速度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **稳定性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **易用性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

### 最佳实践

**推荐配置**: 使用 **YFinance 作为主adapter，AKShare作为补充**

```python
# 优先级配置示例
PRIMARY_ADAPTER = YFinanceAdapter()
FALLBACK_ADAPTER = AKShareAdapter()

# 特殊市场配置
BSE_ADAPTER = AKShareAdapter()  # 北交所专用
CRYPTO_ADAPTER = YFinanceAdapter()  # 加密货币专用
```

### 关键发现

1. **YFinance更全面**: 在资产信息获取和数据完整性上明显领先
2. **AKShare更快**: 在国内网络环境下访问速度优势明显
3. **互补性强**: 两者结合可以覆盖更广泛的市场和资产类型
4. **需要修复**: AKShare的`get_asset_info()`方法存在严重bug，需要优先修复

---

## 测试数据详情

完整测试报告请查看: `adapter_comparison_report.txt`

**测试覆盖的资产**:
- **股票**: 9个（NASDAQ:AAPL, AMEX:GORO, NYSE:JPM, HKEX:00700, SSE:601398, SZSE:002594, SZSE:300750, BSE:835368, CRYPTO:BTC）
- **ETF**: 7个（NASDAQ:QQQ, AMEX:GLD, NYSE:SPY, HKEX:03033, SSE:510050, SZSE:159919, BSE:560800）
- **指数**: 7个（NASDAQ:IXIC, AMEX:RUT, NYSE:DJI, HKEX:HSI, SSE:000001, SZSE:399001, BSE:899050）

**测试交易所**: NASDAQ, NYSE, AMEX, HKEX, SSE, SZSE, BSE, CRYPTO

---

*报告生成时间: 2025-10-23 00:19*  
*测试脚本: test_adapters_comparison.py*

