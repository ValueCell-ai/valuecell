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
</div>

<div align="center">
  <a href="README.md" style="color: gray;">English</a>
  <a href="README.zh.md" style="color: gray;">中文（简体）</a>
  <a href="README.zh_Hant.md" style="color: auto;">中文（繁體）</a>
  <a href="README.ja.md" style="color: gray;">日本語</a>
</div>


# ValueCell
ValueCell 是一個社群驅動的多智能體金融應用產品，我們的計劃是打造全球最大的去中心化金融智能體社群。

它會為您提供頂尖的投資智能體團隊，協助您完成選股、調研、追蹤和交易。

歡迎大家加入Discord社群反饋使用中遇到的問題，以及更多開發者參與共建🔥🔥🔥

>注意：ValueCell團隊人員不會主動私信社群參與者，項目僅為技術交流使用，投資有風險。⚠️

# 產品截圖

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
  <img src="assets/product/NewPushAgent.png" style="width: 100%; height: auto;">
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
- **多家大型語言模型供應商**：支援 OpenRouter、SiliconFlow、Google 與 OpenAI
- **熱門市場資料**：涵蓋美國市場、加密貨幣、香港市場、中國市場等
- **多智能體框架相容**：透過 A2A 協議，支援 LangChain、Agno 等主流 Agent 框架，進行研發整合

# 快速開始

ValueCell 是以 Python 為基礎的應用，並具備完整的前端操作介面。參考下列設定即可快速啟動。

## 前置條件

為了獲得最佳效能與簡化開發流程，建議安裝下列工具：

**[uv](https://docs.astral.sh/uv/getting-started/installation/)** - 以 Rust 構建的超速 Python 套件與專案管理工具  
**[bun](https://github.com/oven-sh/bun#install)** - 高效能的 JavaScript/TypeScript 工具包，整合執行時、打包器、測試與套件管理

## 安裝

1. **克隆倉庫**

   ```bash
   git clone https://github.com/ValueCell-ai/valuecell.git
   cd valuecell
   ```

2. **設定環境變數**

   ```bash
   cp .env.example .env
   ```

   使用您的 API 密鑰與偏好設定編輯 `.env` 檔案。此設定檔會在所有智能體間共用。詳見 [配置指南](docs/CONFIGURATION_GUIDE.md)。

## 設定

更多系統設定詳情說明可以參考[CONFIGURATION_GUIDE](./docs/CONFIGURATION_GUIDE.md)

### 模型供應商
透過編輯 `.env` 檔案來設定您偏好的模型供應商：

- **簡易配置**：僅需配置模型廠商 API Key 即可

- **其他配置**：對於調研類型的 Agent 來說，需要配置更多環境變數，可以仔細閱讀 `.env.example` 中的說明

- **官方推薦**：配置 OpenRouter + 任意提供嵌入模型的供應商。原因：可以快速實現多廠商模型切換，以及 RAG+Memory 的 AI 能力
  

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

## 存取介面

- **Web UI**：於瀏覽器開啟 [http://localhost:1420](http://localhost:1420)
- **日誌**：在 `logs/{timestamp}/*.log` 檢視應用程式日誌，追蹤後端服務與各智能體的詳細執行資訊

## 最後

應用程式啟動後，您可以透過 Web 介面使用整合於 ValueCell 的各種 Agents。

---

**注意**：啟動應用程式前，請確認所有前置條件已安裝且環境變數正確設定。
若長時間未有更新，可以刪除專案中的資料庫檔案 `lancedb/`、`valuecell.db`、`.knowledgebase/` 後重新啟動。


# 開發者

誠摯邀請每位開發者加入 Discord 討論組，我們會定期交流社群 RoadMap 以及未來社群貢獻者權益規劃

開發流程及標準詳見:[CONTRIBUTING.md](.github/CONTRIBUTING.md)

# 路線圖

## 🤖 強化智能體能力
### 交易能力
- **加密貨幣**：支援 OKX、Binance 交易所，更多交易所規劃接入中…
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
