import dayjs from "dayjs";
import { useSettingsStore } from "@/store/settings-store";

// Language-specific format configurations
const FORMAT_CONFIGS = {
  "en-US": {
    date: "MM/DD/YYYY",
    time: "hh:mm A",
    datetime: "MM/DD/YYYY hh:mm A",
    currency: "USD",
    locale: "en-us",
  },
  "en-GB": {
    date: "DD/MM/YYYY",
    time: "HH:mm",
    datetime: "DD/MM/YYYY HH:mm",
    currency: "GBP",
    locale: "en-gb",
  },
  "zh-Hans": {
    date: "YYYY年MM月DD日",
    time: "HH:mm",
    datetime: "YYYY年MM月DD日 HH:mm",
    currency: "CNY",
    locale: "zh-cn",
  },
  "zh-Hant": {
    date: "YYYY年MM月DD日",
    time: "HH:mm",
    datetime: "YYYY年MM月DD日 HH:mm",
    currency: "HKD", // Defaulting to HKD for Traditional Chinese context usually
    locale: "zh-tw",
  },
  "ja-JP": {
    date: "YYYY/MM/DD",
    time: "HH:mm",
    datetime: "YYYY/MM/DD HH:mm",
    currency: "JPY",
    locale: "ja",
  },
} as const;

type LanguageCode = keyof typeof FORMAT_CONFIGS;

function getConfig(language: string) {
  return (
    FORMAT_CONFIGS[language as LanguageCode] || FORMAT_CONFIGS["en-US"]
  );
}

function getCurrentLanguage() {
  return useSettingsStore.getState().language;
}

/**
 * Format a date string or object according to the current language settings
 */
export function formatDate(
  date: string | Date | number | undefined | null,
  language?: string
) {
  if (!date) return "";
  const config = getConfig(language || getCurrentLanguage());
  return dayjs(date).format(config.date);
}

/**
 * Format a time string or object according to the current language settings
 */
export function formatTime(
  date: string | Date | number | undefined | null,
  language?: string
) {
  if (!date) return "";
  const config = getConfig(language || getCurrentLanguage());
  return dayjs(date).format(config.time);
}

/**
 * Format a datetime string or object according to the current language settings
 */
export function formatDateTime(
  date: string | Date | number | undefined | null,
  language?: string
) {
  if (!date) return "";
  const config = getConfig(language || getCurrentLanguage());
  return dayjs(date).format(config.datetime);
}

/**
 * Format a number according to the current language settings
 */
export function formatNumber(
  number: number | undefined | null,
  options?: Intl.NumberFormatOptions,
  language?: string
) {
  if (number === undefined || number === null) return "";
  const lang = language || getCurrentLanguage();
  return new Intl.NumberFormat(lang, options).format(number);
}

/**
 * Format a currency amount according to the current language settings
 */
export function formatCurrency(
  amount: number | undefined | null,
  currency?: string,
  language?: string
) {
  if (amount === undefined || amount === null) return "";
  const lang = language || getCurrentLanguage();
  const config = getConfig(lang);
  
  return new Intl.NumberFormat(lang, {
    style: "currency",
    currency: currency || config.currency,
  }).format(amount);
}
