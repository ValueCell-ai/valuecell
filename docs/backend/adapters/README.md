# 资产数据适配器（Asset Adapters）

路径：`python/valuecell/adapters/assets/`

资产数据适配器层负责从不同数据源获取行情数据（实时价格、历史价格、资产信息、搜索），并通过统一接口暴露给上层服务。

---

## 模块文件

| 文件 | 类 | 职责 |
|------|-----|------|
| `base.py` | `BaseDataAdapter` | 所有适配器的抽象基类 |
| `yfinance_adapter.py` | `YFinanceAdapter` | 雅虎财经（美股、港股、加密货币） |
| `akshare_adapter.py` | `AKShareAdapter` | AKShare（A 股、港股） |
| `manager.py` | `AdapterManager`, `WatchlistManager` | 适配器路由管理 + 观察列表管理 |
| `types.py` | `Asset`, `AssetPrice`, `AssetSearchResult`, ... | 统一数据类型定义 |
| `i18n_integration.py` | — | 多语言资产名称支持 |

---

## 统一 Ticker 格式

所有适配器使用 `EXCHANGE:SYMBOL` 格式作为内部唯一标识：

| 交易所 | 格式 | 示例 |
|--------|------|------|
| NASDAQ | `NASDAQ:SYMBOL` | `NASDAQ:AAPL` |
| NYSE | `NYSE:SYMBOL` | `NYSE:JPM` |
| AMEX | `AMEX:SYMBOL` | `AMEX:GLD` |
| HKEX | `HKEX:5位数字（含前导零）` | `HKEX:00700` |
| SSE（上交所） | `SSE:6位代码` | `SSE:601398` |
| SZSE（深交所） | `SZSE:6位代码` | `SZSE:000001` |
| BSE（北交所） | `BSE:6位代码` | `BSE:835368` |
| CRYPTO | `CRYPTO:SYMBOL` | `CRYPTO:BTC` |

---

## 数据类型

### Asset（资产信息）

```python
class Asset:
    ticker: str                 # 内部 Ticker
    asset_type: AssetType       # STOCK / ETF / CRYPTO / INDEX / BOND
    names: AssetNames           # 多语言名称
    market_info: MarketInfo     # 交易所、国家、货币
    sector: Optional[str]
    industry: Optional[str]
```

### AssetPrice（价格数据）

```python
class AssetPrice:
    ticker: str
    current_price: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    change: float               # 涨跌额
    change_percent: float       # 涨跌幅
    timestamp: datetime
    data_source: DataSource
```

### AssetSearchResult（搜索结果）

```python
class AssetSearchResult:
    ticker: str
    asset_type: AssetType
    names: List[str]            # 多语言名称列表
    exchange: Exchange
    country: str
    relevance_score: float      # 相关性评分（用于排序）
```

---

## BaseDataAdapter（抽象基类）

所有适配器必须实现的接口：

```python
class BaseDataAdapter(ABC):
    @abstractmethod
    def get_capabilities(self) -> List[AdapterCapability]:
        """返回此适配器支持的交易所/资产类型组合"""

    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """验证 ticker 是否属于此适配器支持范围"""

    @abstractmethod
    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """获取资产详细信息"""

    @abstractmethod
    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """获取实时价格"""

    @abstractmethod
    def get_multiple_prices(self, tickers: List[str]) -> Dict[str, Optional[AssetPrice]]:
        """批量获取价格（并行优化）"""

    @abstractmethod
    def get_historical_prices(self, ticker, start_date, end_date, interval) -> List[AssetPrice]:
        """获取历史价格"""

    @abstractmethod
    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """搜索资产"""
```

---

## AdapterManager（适配器路由管理器）

`AdapterManager` 通过路由表将请求分发到正确的适配器，并提供自动故障转移（failover）。

### 路由机制

```
ticker = "NASDAQ:AAPL"
    │  exchange = "NASDAQ"
    ▼
exchange_routing["NASDAQ"] = [YFinanceAdapter, ...]
    │  首个通过 validate_ticker() 的适配器获胜
    ▼
YFinanceAdapter.get_real_time_price("NASDAQ:AAPL")
    │  成功 → 返回
    │  失败 → 尝试下一个 failover 适配器
    ▼
结果写入 _ticker_cache（下次快速命中）
```

### 并行搜索

`search_assets()` 使用 `ThreadPoolExecutor` 并行查询所有适配器，并对结果去重：

```python
with ThreadPoolExecutor(max_workers=len(target_adapters)) as executor:
    future_to_adapter = {
        executor.submit(adapter.search_assets, query): adapter
        for adapter in target_adapters
    }
    # 等待所有完成，合并结果
```

### LLM Fallback 搜索

当所有适配器均无结果时，触发基于 LLM 的兜底搜索（`_fallback_search_assets`）：
1. 调用 `PRODUCT_MODEL_ID` 模型生成可能的 Ticker 列表
2. 逐个调用 `get_asset_info()` 验证是否真实存在
3. 返回验证通过的结果

---

## 各适配器支持范围

### YFinanceAdapter

| 支持范围 | 说明 |
|----------|------|
| 美股 | NASDAQ / NYSE / AMEX |
| 港股 | HKEX（代码格式：`0700.HK`）|
| 加密货币 | CRYPTO（格式：`BTC-USD`）|
| 数据质量 | 实时（延迟约 15 分钟），历史数据完整 |
| 中国可用性 | 部分地区可能需要代理 |

### AKShareAdapter

| 支持范围 | 说明 |
|----------|------|
| A 股 | SSE（上交所）、SZSE（深交所）、BSE（北交所）|
| 港股 | HKEX |
| 数据质量 | 实时（延迟约 15 分钟），免费 |
| 限制 | 频率过高可能触发限流 |

---

## WatchlistManager（观察列表管理）

`WatchlistManager` 提供用户观察列表的增删查功能，并集成 `AdapterManager` 批量获取价格：

```python
manager = WatchlistManager(adapter_manager)

# 创建观察列表
watchlist = manager.create_watchlist(user_id="u1", name="我的自选")

# 添加股票
manager.add_asset_to_watchlist(user_id="u1", ticker="NASDAQ:AAPL")

# 批量获取价格
prices = manager.get_watchlist_prices(user_id="u1")
# 返回 {"NASDAQ:AAPL": AssetPrice(...), ...}
```

---

## 全局单例

```python
from valuecell.adapters.assets import get_adapter_manager, get_watchlist_manager

adapter_manager = get_adapter_manager()   # 全局单例 AdapterManager
watchlist_manager = get_watchlist_manager()  # 全局单例 WatchlistManager
```

在 FastAPI 应用启动时（`lifespan`），系统会自动初始化并配置 YFinance 和 AKShare 适配器：

```python
manager.configure_yfinance()
manager.configure_akshare()
```
