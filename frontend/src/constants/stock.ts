// Stock color definitions
export const GREEN_COLOR = "#15803d";
export const RED_COLOR = "#E25C5C";
export const NEUTRAL_COLOR = "#707070";

export const GREEN_GRADIENT: [string, string] = [
  "rgba(21, 128, 61, 0.6)",
  "rgba(21, 128, 61, 0)",
];
export const RED_GRADIENT: [string, string] = [
  "rgba(226, 92, 92, 0.5)",
  "rgba(226, 92, 92, 0)",
];
export const NEUTRAL_GRADIENT: [string, string] = [
  "rgba(112, 112, 112, 0.5)",
  "rgba(112, 112, 112, 0)",
];

export const GREEN_BADGE = { bg: "#f0fdf4", text: "#15803d" };
export const RED_BADGE = { bg: "#FFEAEA", text: "#E25C5C" };
export const NEUTRAL_BADGE = { bg: "#F5F5F5", text: "#707070" };

/**
 * Stock configurations for home page display.
 * Used as fallback when /api/v1/system/default-tickers API fails.
 * The API returns region-appropriate stocks based on user's IP location.
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
