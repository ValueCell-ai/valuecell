import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { StockChangeType } from "@/types/stock";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Converts currency code to symbol
 * @param currencyCode - Currency code (e.g., "USD", "CNY", "HKD") - NOT currency symbols
 * @returns Currency symbol (e.g., "$", "¥", "HK$")
 */
function getCurrencySymbol(currencyCode: string): string {
  const currencyMap: Record<string, string> = {
    USD: "$",
    CNY: "¥",
    HKD: "HK$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
    KRW: "₩",
  };
  return currencyMap[currencyCode] || currencyCode;
}

/**
 * Formats a numeric price with currency symbol
 * @param price - The numeric price value
 * @param currency - Currency code (e.g., "USD", "CNY", "HKD")
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted price string with currency symbol
 * @example formatPrice(1234.567, "USD") // "$1234.57"
 * @example formatPrice(1234.567, "CNY") // "¥1234.57"
 */
export function formatPrice(
  price: number,
  currency: string,
  decimals: number = 2,
): string {
  const symbol = getCurrencySymbol(currency);
  return `${symbol}${price.toFixed(decimals)}`;
}

/**
 * Formats a percentage change with appropriate sign and styling
 * @param changePercent - The percentage change value (can be positive, negative, or zero)
 * @param decimals - Number of decimal places (default: 2)
 * @param suffix - Suffix to add to the percentage string (default: "")
 * @returns Formatted percentage string with sign
 */
export function formatChange(
  changePercent: number,
  suffix: string = "",
  decimals: number = 2,
): string {
  if (changePercent === 0) {
    return `${changePercent.toFixed(decimals)}${suffix}`;
  }

  const sign = changePercent > 0 ? "+" : "-";
  const value = Math.abs(changePercent).toFixed(decimals);
  return `${sign}${value}${suffix}`;
}

/**
 * Get stock change type based on change percentage and currency
 * @param changePercent - The percentage change
 * @param currency - The currency code (e.g., "USD", "CNY", "HKD") - NOT currency symbols
 * @returns The change type (positive/negative/neutral)
 *
 * Note: Chinese stock markets (CNY) use inverted colors:
 * - Positive change (up) -> Red
 * - Negative change (down) -> Green
 *
 * Western stock markets (USD, EUR, etc.) use standard colors:
 * - Positive change (up) -> Green
 * - Negative change (down) -> Red
 */
export function getChangeType(
  changePercent: number,
  currency = "USD",
): StockChangeType {
  const isChinese = currency.toUpperCase() === "CNY";

  if (changePercent === 0) {
    return "neutral";
  }

  // For Chinese markets, invert the color logic
  if (isChinese) {
    return changePercent > 0 ? "negative" : "positive";
  }

  // For other markets, use standard logic
  return changePercent > 0 ? "positive" : "negative";
}
