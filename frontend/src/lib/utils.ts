import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { StockChangeType } from "@/types/stock";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formats a numeric price with currency symbol
 * @param price - The numeric price value
 * @param currency - Currency symbol (e.g., "$", "¥", "€")
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted price string with currency symbol
 * @example formatPrice(1234.567, "$") // "$1234.57"
 */
export function formatPrice(
  price: number,
  currency: string,
  decimals: number = 2,
): string {
  return `${currency}${price.toFixed(decimals)}`;
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
 * Determines the type of change based on percentage value
 * @param changePercent - The percentage change value
 * @returns Change type: "positive", "negative", or "neutral"
 */
export function getChangeType(changePercent: number): StockChangeType {
  return changePercent > 0
    ? "positive"
    : changePercent < 0
      ? "negative"
      : "neutral";
}
