export type StockChangeType = "positive" | "negative" | "neutral";

export interface Watchlist {
  name: string;
  items: Stock[];
}

export interface Stock {
  ticker: string;
  asset_type: "stock" | "etf" | "index" | "crypto";
  display_name: string;
  symbol: string;
  exchange: string;
}

export type StockCurrency = "USD" | "CNY" | "HKD";

export interface StockPrice {
  ticker: string;
  price: number;
  price_formatted: string;
  timestamp: string;
  change: number;
  change_percent?: number;
  market_cap_formatted: string;
  source: string;
  currency: StockCurrency;
}

/**
 * Standard interval format for historical data
 * Format: <number><unit>
 * Examples: "1m", "5m", "15m", "30m", "60m", "1h", "1d", "1w", "1mo"
 */
export type StockInterval =
  | "1m" // 1 minute
  | "1h" // 1 hour
  | "1d" // 1 day (default)
  | "1w"; // 1 week

export interface StockHistory {
  time: string;
  price: number;
}

export interface StockDetail {
  display_name: string;
  properties: {
    sector: string;
    industry: string;
    market_cap: number;
    pe_ratio: number;
    dividend_yield: number;
    beta: number;
    website: string;
    business_summary: string;
  };
}
