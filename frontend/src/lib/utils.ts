import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { StockChangeType } from "@/types/stock";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const isNullOrUndefined = (value: unknown): value is undefined | null =>
  value === undefined || value === null;

export function numberFixed(number?: number, decimals = 2): string {
  if (isNullOrUndefined(number)) return "-";

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
    useGrouping: false,
  }).format(number);
}

/**
 * Format price with currency symbol
 */
export function formatPrice(price: number, currency: string, decimals = 2) {
  const currencyMap: Record<string, string> = {
    USD: "$",
    CNY: "¥",
    HKD: "HK$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
    KRW: "₩",
  };

  const symbol = currencyMap[currency] || currency;
  return `${symbol}${numberFixed(price, decimals)}`;
}

/**
 * Format percentage change with sign
 */
export function formatChange(
  changePercent?: number,
  suffix = "",
  decimals = 2,
): string {
  if (isNullOrUndefined(changePercent)) return "N/A";
  const sign = changePercent > 0 ? "+" : "-";
  const value = numberFixed(Math.abs(changePercent), decimals);
  if (value === "0") return `${value}${suffix}`;
  return `${sign}${value}${suffix}`;
}

/**
 * Get stock change type: "positive" (up), "negative" (down), or "neutral" (no change)
 */
export function getChangeType(changePercent?: number): StockChangeType {
  if (isNullOrUndefined(changePercent) || changePercent === 0) {
    return "neutral";
  }
  return changePercent > 0 ? "positive" : "negative";
}

export const getCoinCapIcon = (symbol: string) => {
  const fixedSymbol = symbol.split(/[-/]/)[0].toLowerCase();
  return `https://assets.coincap.io/assets/icons/${fixedSymbol}@2x.png`;
};
