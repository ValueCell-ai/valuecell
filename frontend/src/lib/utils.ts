import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { StockChangeType } from "@/types/stock";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const isNullOrUndefined = (value: unknown): value is undefined | null =>
  value === undefined || value === null;

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
 * Format price with currency symbol
 */
export function formatPrice(
  price: number,
  currency: string,
  decimals = 2,
): string {
  const symbol = getCurrencySymbol(currency);
  return `${symbol}${price.toFixed(decimals)}`;
}

/**
 * Format percentage change with sign
 */
export function formatChange(
  changePercent: number | null,
  suffix = "",
  decimals = 2,
): string {
  if (isNullOrUndefined(changePercent)) return "N/A";
  if (changePercent === 0) return `${changePercent.toFixed(decimals)}${suffix}`;

  const sign = changePercent > 0 ? "+" : "-";
  const value = Math.abs(changePercent).toFixed(decimals);
  return `${sign}${value}${suffix}`;
}

/**
 * Get stock change type: "positive" (up), "negative" (down), or "neutral" (no change)
 */
export function getChangeType(changePercent: number | null): StockChangeType {
  if (isNullOrUndefined(changePercent) || changePercent === 0) {
    return "neutral";
  }
  return changePercent > 0 ? "positive" : "negative";
}
