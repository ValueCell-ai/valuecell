import type { StockChangeType } from "@/types/stock";

/**
 * Stock change type color mappings
 *
 * Note: The semantic meaning of "positive" and "negative" depends on the market:
 * - Western markets (USD, EUR, etc.): positive = green (up), negative = red (down)
 * - Chinese markets (CNY, HKD): positive = red (up), negative = green (down)
 *
 * The getChangeType() function in utils.ts handles this logic automatically
 * based on the currency code, so these colors will be applied correctly.
 */
export const STOCK_COLORS: Record<StockChangeType, string> = {
  positive: "#15803d", // Green for western markets (up), used for chinese markets (down)
  negative: "#E25C5C", // Red for western markets (down), used for chinese markets (up)
  neutral: "#707070", // Gray for no change
};

/**
 * Stock change type gradient color mappings
 * @see STOCK_COLORS for color semantics
 */
export const STOCK_GRADIENT_COLORS: Record<StockChangeType, [string, string]> =
  {
    positive: ["rgba(21, 128, 61, 0.6)", "rgba(21, 128, 61, 0)"],
    negative: ["rgba(226, 92, 92, 0.5)", "rgba(226, 92, 92, 0)"],
    neutral: ["rgba(112, 112, 112, 0.5)", "rgba(112, 112, 112, 0)"],
  };

/**
 * Stock change type badge color mappings (for percentage change display)
 * @see STOCK_COLORS for color semantics
 */
export const STOCK_BADGE_COLORS: Record<
  StockChangeType,
  { bg: string; text: string }
> = {
  positive: { bg: "#f0fdf4", text: "#15803d" },
  negative: { bg: "#FFEAEA", text: "#E25C5C" },
  neutral: { bg: "#F5F5F5", text: "#707070" },
};

/**
 * Stock configurations for home page display
 * - ticker: Full ticker identifier (e.g., "NASDAQ:IXIC")
 * - symbol: Display name/abbreviation for the stock (e.g., "NASDAQ", "HSI") - NOT currency symbol
 */
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
