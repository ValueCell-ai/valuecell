export type StockChangeType = "positive" | "negative" | "neutral";

export interface Stock {
  ticker: string;
  asset_type: "stock" | "etf" | "index" | "crypto";
  display_name: string;
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


