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
  | "5m" // 5 minutes
  | "15m" // 15 minutes
  | "30m" // 30 minutes
  | "60m" // 60 minutes
  | "1h" // 1 hour
  | "1d" // 1 day (default)
  | "1w" // 1 week
  | "1mo"; // 1 month

export interface StockHistory {
  ticker: string;
  interval: StockInterval;
  prices: {
    ticker: string;
    price: number;
    timestamp: string;
    open_price: number;
    high_price: number;
    low_price: number;
    close_price: number;
    volume: number;
    change: number;
    change_percent?: number;
    currency: StockCurrency;
    source: string;
  }[];
}

export interface StockDetail {
  ticker: string;
  asset_type: "stock" | "etf" | "index" | "crypto";
  asset_type_display: string;
  names: {
    "en-US": string;
    "en-GB": string;
    "zh-Hans": string;
    "zh-Hant": string;
  };
  display_name: string;
  descriptions: Record<string, string>;
  market_info: {
    exchange: string;
    country: string;
    currency: StockCurrency;
    timezone: string;
    trading_hours: string | null;
    market_status: string;
  };
  source_mappings: Record<string, string>;
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
  created_at: string;
  updated_at: string;
  is_active: boolean;
}
