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

export interface StockPrice {
  ticker: string;
  price_formatted: string;
  timestamp: string;
  change: number;
  change_percent_formatted: string;
  market_cap_formatted: string;
  source: string;
}

export interface StockHistory {
  ticker: string;
  interval: "m" | "h" | "d" | "w" | "mo" | "y";
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
    change_percent: number;
    currency: string;
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
    currency: string;
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
