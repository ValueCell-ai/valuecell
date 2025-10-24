import type { StockChangeType } from "@/types/stock";

// Stock change type color mappings
export const STOCK_COLORS: Record<StockChangeType, string> = {
  positive: "#15803d",
  negative: "#E25C5C",
  neutral: "#707070",
};

// Stock change type gradient color mappings
export const STOCK_GRADIENT_COLORS: Record<StockChangeType, [string, string]> =
  {
    positive: ["rgba(21, 128, 61, 0.6)", "rgba(21, 128, 61, 0)"],
    negative: ["rgba(226, 92, 92, 0.5)", "rgba(226, 92, 92, 0)"],
    neutral: ["rgba(112, 112, 112, 0.5)", "rgba(112, 112, 112, 0)"],
  };

// Stock change type badge color mappings (for percentage change display)
export const STOCK_BADGE_COLORS: Record<
  StockChangeType,
  { bg: string; text: string }
> = {
  positive: { bg: "#f0fdf4", text: "#15803d" },
  negative: { bg: "#FFEAEA", text: "#E25C5C" },
  neutral: { bg: "#F5F5F5", text: "#707070" },
};

export const HOME_STOCK_SHOW = [
  {
    ticker: "NASDAQ:IXIC",
    symbol: "NASDAQ",
  },
  {
    ticker: "HKEX:HSI",
    symbol: "HSI",
  },
  {
    ticker: "SSE:000001",
    symbol: "SSE",
  },
] as const;
