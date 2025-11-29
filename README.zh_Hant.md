<p align="center">
  <img src="assets/valuecell.png" style="width: 100%; height: auto;">
</p>

<div align="center" style="line-height: 2;">
    <a href="https://www.python.org/downloads" target="_blank">
        <img src="https://img.shields.io/badge/python-3.12+-blue.svg"
            alt="Python version"></a>
    <a href="LICENSE" target="_blank">
        <img src="https://img.shields.io/badge/license-Apache2.0-red.svg"
            alt="License: Apache2.0"></a>  
    <br>
    <a href="https://discord.com/invite/84Kex3GGAh" target="_blank">
        <img src="https://img.shields.io/discord/1399603591471435907?logo=discord&labelColor=%20%235462eb&logoColor=%20%23f5f5f5&color=%20%235462eb"
            alt="chat on Discord"></a>
    <a href="https://twitter.com/intent/follow?screen_name=valuecell" target="_blank">
        <img src="https://img.shields.io/twitter/follow/valuecell?logo=X&color=%20%23f5f5f5"
            alt="follow on X(Twitter)"></a>
    <a href="https://www.linkedin.com/company/valuecell/" target="_blank">
        <img src="https://custom-icon-badges.demolab.com/badge/LinkedIn-0A66C2?logo=linkedin-white&logoColor=fff"
            alt="follow on LinkedIn"></a>
    <a href="https://www.facebook.com/people/ValueCell/61581410516790/" target="_blank">
        <img src="https://custom-icon-badges.demolab.com/badge/Facebook-1877F2?logo=facebook-white&logoColor=fff"
            alt="follow on Facebook"></a>
    <a href="https://www.youtube.com/watch?v=C3tfHyGY9YE" target="_blank">
        <img src="https://img.shields.io/badge/Watch%20on-YouTube-red?logo=youtube"
            alt="Watch on YouTube"></a>
</div>

<div align="center">
  <a href="README.md" style="color: auto;">English</a>
  <a href="README.zh.md" style="color: auto;">中文（简体）</a>
  <a href="README.zh_Hant.md" style="color: gray;">中文（繁體）</a>
  <a href="README.ja.md" style="color: auto;">日本語</a>
</div>


# ValueCell
ValueCell 是一個社群驅動的多智能體金融應用產品，我們的計劃是打造全球最大的去中心化金融智能體社群。

它會為您提供頂尖的投資智能體團隊，協助您完成選股、調研、追蹤和交易。

系統會將您的敏感資訊完全託管在本地，保證核心資料安全。

歡迎大家加入Discord社群反饋使用中遇到的問題，以及更多開發者參與共建🔥🔥🔥

>注意：ValueCell團隊人員不會主動私信社群參與者，項目僅為技術交流使用，投資有風險。⚠️

# 產品截圖

[![觀看影片](https://img.youtube.com/vi/C3tfHyGY9YE/maxresdefault.jpg)](https://www.youtube.com/watch?v=C3tfHyGY9YE)

<p align="center">
  <img src="assets/product/homepage.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/product/superagent.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/product/AutoTradingAgent.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/product/Model_Configuration.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/product/agent_market.png" style="width: 100%; height: auto;">
</p>

# 核心功能

<p align="center">
  <img src="assets/architecture.png" style="width: 100%; height: auto;">
</p>


## 多智能體系統
- **DeepResearch Agent**：獲取並分析股票的基本面文件，輸出準確的數據與可解釋的總結
- **Strategy Agent**：支援多種加密資產、多策略智慧交易，自動執行你的策略
- **News Retrieval Agent**: 支援個人化定時任務的新聞推送，及時追蹤關鍵資訊
- **其他智能體**：更多智能體正在規劃中...

## 彈性整合
- **多家大型語言模型供應商**：支援 OpenRouter、SiliconFlow、Openai-compatible、Azure、Google、OpenAI 與 DeepSeek
- **熱門市場資料**：涵蓋美國市場、加密貨幣、香港市場、中國市場等
- **多智能體框架相容**：透過 A2A 協議，支援 LangChain、Agno 等主流 Agent 框架，進行研發整合
**交易所連接**：支援即時路由至 OKX 和 Binance，並內建安全防護機制

# 快速開始

## 新使用者

若要快速開始使用，請從 GitHub 的[發布頁面](https://github.com/ValueCell-ai/valuecell/releases)下載適用於 MacOS 或 Windows 的最新 ValueCell 應用程式。您也可以從我們的官方網站 [https://valuecell.ai](https://valuecell.ai) 下載應用程式。

安裝後，使用 ValueCell 前請先設定您偏好的模型供應商。請參閱應用程式內的指示或文件。

### 即時交易

- 配置 AI 模型: 透過網頁介面新增你的 AI 模型 API Key。
- 配置交易所: 設定 Binance/HyperLiquid/OKX/Coinbase... API 憑證
- 建立策略: 將 AI 模型與交易所組合，建立自訂交易策略
- 監控與控制: 透過即時監控啟動/停止策略，並監控交易表現
- 注意：當前僅支援合約交易（現貨以1X合約實現），所以請確保合約帳戶存在餘額

#### 支援的交易所

| 交易所 | 說明 | 狀態 |
| --- | --- | --- |
| **Binance** | 僅支援國際站 [binance.com](binance.com)，不支援美國站。使用 USDT-M 合約（USDT 本位合約）。請確保您的合約帳戶有足夠的 USDT 餘額。交易對格式：`BTC/USDT`。 Note：確保永續合約帳戶不為0。 申請API添加IP白名單通過搜索引擎搜索`My IP`查看 | ✅ 已測試 |
| **Hyperliquid** | 僅支援 USDC 作為保證金貨幣。使用您的主錢包地址 + API 錢包私鑰認證（使用 [API 頁面](https://app.hyperliquid.xyz/API) 申請）。市價單會自動轉換為 IoC 限價單。交易對格式必須手動調整為 `SYMBOL/USDC`（例如 `WIF/USDC`）配置地址為主錢包地址+API錢包私鑰 每次交易至少10U | ✅ 已測試 |
| **OKX** | 需要 API Key、Secret 和 Passphrase（OKX帳號密碼） 進行認證。支援 USDT 本位合約。交易對格式：`BTC/USDT`。 | ✅ 已測試 |
| Coinbase | 支援 USDT 本位合約。Coinbase International 尚未支援 | 🟡 部分測試 |
| Gate.io | 支援 USDT 本位合約。需要 API Key 和 Secret | 🟡 部分測試 |
| MEXC | 支援 USDT 本位合約。需要 API Key 和 Secret | 🟡 部分測試 |
| Blockchain | 支援 USDT 本位合約。需要 API Key 和 Secret | 🟡 部分測試 |

**圖例**:
- ✅ **已測試**: 在生產環境中經過充分測試和驗證
- 🟡 **部分測試**: 程式碼實作已完成但未完全測試，可能需要除錯
- **推薦**: 優先使用經過充分測試的交易所（Binance, Hyperliquid, OKX）

### 注意事項
- 目前僅支援槓桿/合約交易，因此您需要確保您的永續合約（Perps）帳戶有足夠的餘額。
- 您必須妥善保管您的 API 密鑰以避免資金損失。該應用程式將密鑰本地儲存在您的裝置上，不會透過網際網路發送給任何第三方。
- 為了確保您的帳戶安全，您需要定期重設您的 API 密鑰。

---

**注意**：啟動應用程式前，請確認所有前置條件已安裝且環境變數正確設定。
若長時間未有更新，可以刪除本地資料並重新啟動：
- LanceDB 目錄（位於系統應用程式目錄，與 `.env` 同路徑）：
  - macOS: `~/Library/Application Support/ValueCell/lancedb`
  - Linux: `~/.config/valuecell/lancedb`
  - Windows: `%APPDATA%\\ValueCell\\lancedb`
- 知識目錄（位於系統應用程式目錄，與 `.env` 同路徑）：
  - macOS: `~/Library/Application Support/ValueCell/.knowledge`
  - Linux: `~/.config/valuecell/.knowledge`
  - Windows: `%APPDATA%\\ValueCell\\.knowledge`
- SQLite 資料庫檔案（位於系統應用程式目錄，與 `.env` 同路徑）：
  - macOS: `~/Library/Application Support/ValueCell/valuecell.db`
  - Linux: `~/.config/valuecell/valuecell.db`
  - Windows: `%APPDATA%\\ValueCell\\valuecell.db`


## 開發者

誠摯邀請每位開發者加入 Discord 討論組，我們會定期交流社群 RoadMap 以及未來社群貢獻者權益規劃

開發流程及標準詳見:[CONTRIBUTING.md](.github/CONTRIBUTING.md)

ValueCell 是一個基於Python的應用程式，且有完備的前端操作頁面，支援多端應用。可以參考下面配置快速運行。

## 克隆倉庫

   ```bash
   git clone https://github.com/ValueCell-ai/valuecell.git
   cd valuecell
   ```

## 啟動應用程式

啟動完整應用程式（前端、後端與智能體）：

### Linux / Macos
```bash
bash start.sh
```

### Windows (PowerShell)
```powershell
.\start.ps1
```

### 存取介面

- **Web UI**：於瀏覽器開啟 [http://localhost:1420](http://localhost:1420)
- **日誌**：在終端即可查看應用程式日誌，追蹤後端服務與各智能體的詳細執行資訊

### 下一步

應用程式啟動後，你可以透過網頁介面探索並使用 ValueCell 的各項功能與能力

### 設定

更多系統設定詳情說明可以參考[CONFIGURATION_GUIDE](./docs/CONFIGURATION_GUIDE.md)

# 路線圖

## 🤖 強化智能體能力
### 交易能力
- **加密貨幣**：支援 OKX、Binance、Hyperliquid交易所，更多交易所規劃接入中…
- **證券**：逐步支援 AI 證券交易

### 市場擴展
- **歐洲市場**：新增對富時指數、DAX、CAC 40 與其他歐洲交易所的支援
- **亞洲市場**：擴展對日經指數與新興亞洲市場的覆蓋
- **大宗商品市場**：石油、黃金、白銀與農產品分析
- **外匯市場**：主要貨幣對與交叉貨幣分析

### 資產類別多樣化
- **固定收益**：政府債券、企業債券與殖利率分析智能體
- **衍生性商品**：選擇權、期貨與複雜金融工具
- **另類投資**：民間股權、對沖基金與風險投資分析

### 高級通知與推送類型
- **即時警示**：價格波動、成交量激增與技術突破
- **定期報告**：每日／每週／每月投組摘要
- **事件驅動通知**：財報發布、股息公告、監管變動
- **自訂觸發器**：使用者自定義條件與閾值
- **多通道推送**：Discord 與 webhook 整合

## ⚙️ 產品設定與個人化
### 多端產品化
- **客戶端支援**：逐步支援桌面端、客戶端能力
- **資料庫熱更新**：逐步支援相容性升級

### 國際化 (i18n)
- **多語系支援**：英文、中文（簡體／繁體）、日文、韓文、西班牙文、法文
- **在地化市場資料**：特定地區的金融術語與格式
- **文化適配**：時區、日期格式與貨幣偏好
- **智能體個性在地化**：符合文化的溝通風格

### 令牌與認證管理
- **API 金鑰管理**：第三方 API 金鑰的安全儲存與輪換
- **OAuth 整合**：支援主要金融資料供應商

### 使用者偏好與自訂
- **投資檔案**：風險承受度、投資期間與策略偏好
- **UI/UX 自訂**：深色／淺色模式、儀表板佈局與元件偏好
- **智能體行為**：溝通頻率、分析深度與報告風格
- **投組管理**：自訂基準、效能指標與目標設定

### 記憶與學習系統
- **對話歷史**：跨會話的持久聊天記錄
- **使用者學習**：根據使用者行為的自適應推薦
- **市場記憶**：歷史背景與模式識別
- **偏好演進**：推薦的動態調整

## 🔧 ValueCell SDK 開發
### 核心 SDK 功能
- **Python SDK**：用於智能體整合與客製的核心程式，連接前後端
- **WebSocket 支援**：即時資料串流與雙向通訊

### 智能體整合框架
- **外掛架構**：輕鬆整合第三方智能體與工具
- **智能體註冊表**：社群貢獻智能體的市集

### 開發者工具與文件
- **互動式 API 瀏覽器**：含即時測試的 Swagger/OpenAPI 文件
- **程式範例**：多種程式語言的範例實作
- **測試框架**：單元測試、整合測試與模擬資料提供者


# Star

<div align="center">
<a href="https://www.star-history.com/#ValueCell-ai/valuecell&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=ValueCell-ai/valuecell&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=ValueCell-ai/valuecell&type=Date" />
   <img alt="TradingAgents Star History" src="https://api.star-history.com/svg?repos=ValueCell-ai/valuecell&type=Date" style="width: 80%; height: auto;" />
 </picture>
</a>
</div>

<div align="center">
</div>
