/**
 * Mock data for model trade renderer
 * Backend returns JSON string format
 */

export const mockModelTradeData = JSON.stringify({
  title: "Portfolio Value History - Session AutoTrad",
  data: JSON.stringify([
    ["Time", "deepseek/deepseek-v3.1-terminus"],
    ["2025-10-21 10:45:38", 100000.0],
    ["2025-10-21 10:45:51", 100000.0],
    ["2025-10-21 10:47:10", 100000.0],
    ["2025-10-21 10:48:21", 100000.0],
    ["2025-10-21 10:49:42", 96040.0],
    ["2025-10-21 10:51:00", 96038.70297353639],
    ["2025-10-21 10:52:13", 96036.38855716585],
    ["2025-10-21 10:53:33", 96034.41417761859],
    ["2025-10-21 10:54:51", 96033.1870562167],
    ["2025-10-21 10:56:05", 96033.2831119797],
    ["2025-10-21 10:57:18", 94155.95705403051],
  ]),
  create_time: "2025-10-21 02:57:22",
});

export const mockModelTradeDataMultiple = JSON.stringify({
  title: "Portfolio Value History - Multi Models Comparison",
  data: JSON.stringify([
    [
      "Time",
      "deepseek/deepseek-v3.1-terminus",
      "openai/gpt-4",
      "anthropic/claude-3",
    ],
    ["2025-10-21 10:45:38", 100000.0, 100000.0, 100000.0],
    ["2025-10-21 10:45:51", 100000.0, 100500.0, 99800.0],
    ["2025-10-21 10:47:10", 100000.0, 101200.0, 99500.0],
    ["2025-10-21 10:48:21", 100000.0, 101800.0, 99200.0],
    ["2025-10-21 10:49:42", 96040.0, 102200.0, 98900.0],
    ["2025-10-21 10:51:00", 96038.7, 102500.0, 98600.0],
    ["2025-10-21 10:52:13", 96036.38, 102800.0, 98300.0],
    ["2025-10-21 10:53:33", 96034.41, 103100.0, 98000.0],
    ["2025-10-21 10:54:51", 96033.18, 103400.0, 97700.0],
    ["2025-10-21 10:56:05", 96033.28, 103700.0, 97400.0],
    ["2025-10-21 10:57:18", 94155.95, 104000.0, 97100.0],
  ]),
  create_time: "2025-10-21 02:57:22",
});

/**
 * Mock data for model trade table renderer
 * Shows completed trades, positions, and instance details
 */
export const mockModelTradeTableData = JSON.stringify({
  title: "Trading Instance: trade_20251021_104538_59d5aa9b",
  data: `
## Instance Summary

| Metric | Value |
|--------|-------|
| Instance ID | trade_20251021_104538_59d5aa9b |
| Model | deepseek/deepseek-v3.1-terminus |
| Symbols | BTC-USD, ETH-USD |
| Initial Capital | $100,000.00 |
| Current Value | $96,038.70 |
| Total P&L | $-3,961.30 (-3.96%) |
| Available Cash | $92,236.82 |
| Open Positions | 2 |
| Total Trades | 4 |
| Check Count | 5 |
| Status | 🟢 Active |

## Current Positions

| Symbol | Type | Entry Price | Current Price | Quantity | Unrealized P&L |
|--------|------|-------------|---------------|----------|----------------|
| BTC-USD | LONG | $109,669.50 | $109,595.45 | 0.0175 | $-1.30 |
| ETH-USD | LONG | $3,941.45 | $3,941.45 | 0.4776 | $0.00 |

## Recent Trades

| Time | Symbol | Action | Type | Price | P&L |
|------|--------|--------|------|-------|-----|
| 02:46:55 | BTC-USD | OPENED | LONG | $109,686.36 | N/A |
| 02:48:21 | ETH-USD | OPENED | LONG | $3,942.36 | N/A |
| 02:49:34 | BTC-USD | OPENED | LONG | $109,669.50 | N/A |
| 02:49:42 | ETH-USD | OPENED | LONG | $3,941.45 | N/A |
`,
  filters: ["deepseek/deepseek-v3.1-terminus"],
  table_title: "Instance Details",
  create_time: "2025-10-21 02:51:03",
});

/**
 * Mock data for completed trades view (single object - backward compatible)
 */
export const mockCompletedTradesData = JSON.stringify({
  title: "Completed Trades - All Models",
  data: `
# Completed Trades

**FILTER: ALL MODELS ▼** &nbsp;&nbsp;&nbsp; Showing Last 100 Trades

---

## 🤖 GPT 5 completed a **long** trade on 💎 **ETH!**
*10/21, 12:48 PM*

**Price:** $3,959.1 → $3,845.1  
**Quantity:** 1.51  
**Notional:** $5,978 → $5,806  
**Holding time:** 38h 1M  

**NET P&L:** <span style="color: #DC2626; font-weight: 600;">-$177.44</span>

---

## ☀️ Claude Sonnet 4.5 completed a **long** trade on 💎 **ETH!**
*10/21, 12:32 PM*

**Price:** $3,944 → $3,862.3  
**Quantity:** 9.66  
**Notional:** $38,099 → $37,310  
**Holding time:** 11H 54M  

**NET P&L:** <span style="color: #DC2626; font-weight: 600;">-$823.06</span>

---

## 🔷 Gemini 2.5 Pro completed a **long** trade on 🟡 **BTC!**
*10/21, 12:29 PM*

**Price:** $107,641 → $108,143  
**Quantity:** 0.07  
**Notional:** $7,535 → $7,570  
**Holding time:** 28H 4M  

**NET P&L:** <span style="color: #16A34A; font-weight: 600;">+$28.34</span>

---

## 🔷 Gemini 2.5 Pro completed a **long** trade on 💎 **ETH!**
*10/21, 12:19 PM*

**Price:** $3,883.2 → $3,874.7  
**Quantity:** 2.98  
**Notional:** $11,572 → $11,547  
**Holding time:** 12H 42M  

**NET P&L:** <span style="color: #DC2626; font-weight: 600;">-$35.73</span>

---

## 🔷 Gemini 2.5 Pro completed a **long** trade on 🐶 **DOGE!**
*10/21, 12:17 PM*

**Price:** $0.16779 → $0.16910  
**Quantity:** 15,423  
**Notional:** $2,587 → $2,608  
**Holding time:** 9H 23M  

**NET P&L:** <span style="color: #16A34A; font-weight: 600;">+$18.92</span>

`,
  filters: [
    "openai/gpt-5",
    "anthropic/claude-sonnet-4.5",
    "google/gemini-2.5-pro",
  ],
  table_title: "Completed Trades",
  create_time: "2025-10-21 12:50:00",
});

/**
 * Mock data for array format (new format)
 * Demonstrates multiple tabs with different table_title and filtering
 */
export const mockModelTradeTableArrayData = JSON.stringify([
  // Completed Trades - GPT 5
  {
    title: "GPT 5 Trade 1",
    data: `## 🤖 GPT 5 completed a **long** trade on 💎 **ETH!**
*10/21, 12:48 PM*

**Price:** $3,959.1 → $3,845.1  
**Quantity:** 1.51  
**Notional:** $5,978 → $5,806  
**Holding time:** 38h 1M  

**NET P&L:** <span style="color: #DC2626; font-weight: 600;">-$177.44</span>`,
    filters: ["openai/gpt-5"],
    table_title: "Completed Trades",
    create_time: "2025-10-21 12:48:00",
  },
  // Completed Trades - Claude Sonnet 4.5
  {
    title: "Claude Trade 1",
    data: `## ☀️ Claude Sonnet 4.5 completed a **long** trade on 💎 **ETH!**
*10/21, 12:32 PM*

**Price:** $3,944 → $3,862.3  
**Quantity:** 9.66  
**Notional:** $38,099 → $37,310  
**Holding time:** 11H 54M  

**NET P&L:** <span style="color: #DC2626; font-weight: 600;">-$823.06</span>`,
    filters: ["anthropic/claude-sonnet-4.5"],
    table_title: "Completed Trades",
    create_time: "2025-10-21 12:32:00",
  },
  // Completed Trades - Gemini 2.5 Pro (multiple trades)
  {
    title: "Gemini Trade 1",
    data: `## 🔷 Gemini 2.5 Pro completed a **long** trade on 🟡 **BTC!**
*10/21, 12:29 PM*

**Price:** $107,641 → $108,143  
**Quantity:** 0.07  
**Notional:** $7,535 → $7,570  
**Holding time:** 28H 4M  

**NET P&L:** <span style="color: #16A34A; font-weight: 600;">+$28.34</span>`,
    filters: ["google/gemini-2.5-pro"],
    table_title: "Completed Trades",
    create_time: "2025-10-21 12:29:00",
  },
  {
    title: "Gemini Trade 2",
    data: `## 🔷 Gemini 2.5 Pro completed a **long** trade on 💎 **ETH!**
*10/21, 12:19 PM*

**Price:** $3,883.2 → $3,874.7  
**Quantity:** 2.98  
**Notional:** $11,572 → $11,547  
**Holding time:** 12H 42M  

**NET P&L:** <span style="color: #DC2626; font-weight: 600;">-$35.73</span>`,
    filters: ["google/gemini-2.5-pro"],
    table_title: "Completed Trades",
    create_time: "2025-10-21 12:19:00",
  },
  {
    title: "Gemini Trade 3",
    data: `## 🔷 Gemini 2.5 Pro completed a **long** trade on 🐶 **DOGE!**
*10/21, 12:17 PM*

**Price:** $0.16779 → $0.16910  
**Quantity:** 15,423  
**Notional:** $2,587 → $2,608  
**Holding time:** 9H 23M  

**NET P&L:** <span style="color: #16A34A; font-weight: 600;">+$18.92</span>`,
    filters: ["google/gemini-2.5-pro"],
    table_title: "Completed Trades",
    create_time: "2025-10-21 12:17:00",
  },
  // Open Positions - Different tab
  {
    title: "GPT 5 Position 1",
    data: `## Open Position - 🟡 **BTC**
*Opened: 10/21, 10:30 AM*

**Entry Price:** $108,500  
**Current Price:** $108,750  
**Quantity:** 0.05  
**Notional:** $5,425 → $5,437  
**Holding time:** 2H 15M  

**Unrealized P&L:** <span style="color: #16A34A; font-weight: 600;">+$12.50</span>`,
    filters: ["openai/gpt-5"],
    table_title: "Open Positions",
    create_time: "2025-10-21 12:45:00",
  },
  {
    title: "Claude Position 1",
    data: `## Open Position - 💎 **ETH**
*Opened: 10/21, 11:00 AM*

**Entry Price:** $3,900  
**Current Price:** $3,875  
**Quantity:** 2.5  
**Notional:** $9,750 → $9,687  
**Holding time:** 1H 45M  

**Unrealized P&L:** <span style="color: #DC2626; font-weight: 600;">-$62.50</span>`,
    filters: ["anthropic/claude-sonnet-4.5"],
    table_title: "Open Positions",
    create_time: "2025-10-21 12:45:00",
  },
  {
    title: "Gemini Position 1",
    data: `## Open Position - 🐶 **DOGE**
*Opened: 10/21, 11:30 AM*

**Entry Price:** $0.1685  
**Current Price:** $0.1695  
**Quantity:** 10,000  
**Notional:** $1,685 → $1,695  
**Holding time:** 1H 15M  

**Unrealized P&L:** <span style="color: #16A34A; font-weight: 600;">+$10.00</span>`,
    filters: ["google/gemini-2.5-pro"],
    table_title: "Open Positions",
    create_time: "2025-10-21 12:45:00",
  },
  // Instance Details - Another tab
  {
    title: "DeepSeek Instance",
    data: `## Instance Summary

| Metric | Value |
|--------|-------|
| Instance ID | trade_20251021_104538_59d5aa9b |
| Model | deepseek/deepseek-v3.1-terminus |
| Symbols | BTC-USD, ETH-USD |
| Initial Capital | $100,000.00 |
| Current Value | $96,038.70 |
| Total P&L | $-3,961.30 (-3.96%) |
| Available Cash | $92,236.82 |
| Open Positions | 2 |
| Total Trades | 4 |
| Status | 🟢 Active |`,
    filters: ["deepseek/deepseek-v3.1-terminus"],
    table_title: "Instance Details",
    create_time: "2025-10-21 12:50:00",
  },
]);
