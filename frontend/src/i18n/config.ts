import dayjs from "dayjs";
import "dayjs/locale/en";
import "dayjs/locale/ja";
import "dayjs/locale/zh-cn";
import "dayjs/locale/zh-tw";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "@/i18n/en.json";
import ja from "@/i18n/ja.json";
import zhCN from "@/i18n/zh_CN.json";
import zhTW from "@/i18n/zh_TW.json";

// Browser language to TradingView locale mapping
const BROWSER_LOCALE_MAP: Record<string, string> = {
  "zh-Hans": "zh_CN",
  "zh-Hant": "zh_TW",
  "ja-JP": "ja",
  "ko-KR": "kr",
  "de-DE": "de_DE",
  "fr-FR": "fr",
  "it-IT": "it",
  "es-ES": "es",
  "tr-TR": "tr",
  "pl-PL": "pl",
  "ru-RU": "ru",
  "pt-PT": "br",
  "id-ID": "id",
  "ms-MY": "ms_MY",
  "th-TH": "th_TH",
  "vi-VN": "vi_VN",
  "ca-ES": "ca_ES",
};

// Simple language detection
const getInitialLanguage = () => {
  try {
    // Try to get from localStorage (zustand persist)
    if (typeof localStorage !== "undefined") {
      const settings = localStorage.getItem("valuecell-settings");
      if (settings) {
        const parsed = JSON.parse(settings);
        if (parsed.state?.language) {
          return parsed.state.language;
        }
      }
    }
  } catch (_e) {
    // Ignore error
  }

  // Fallback to navigator
  if (typeof navigator !== "undefined") {
    const navLang = navigator.language;

    // Check exact match in map
    if (BROWSER_LOCALE_MAP[navLang]) {
      return BROWSER_LOCALE_MAP[navLang];
    }

    // Special handling for variations
    if (navLang === "zh-CN") return "zh_CN";
    if (navLang === "zh-TW" || navLang === "zh-HK") return "zh_TW";
    if (navLang.startsWith("ja")) return "ja";
  }

  return "en";
};

i18n.use(initReactI18next).init({
  lng: getInitialLanguage(),
  fallbackLng: "en",
  debug: import.meta.env.DEV,
  interpolation: {
    escapeValue: false, // not needed for react as it escapes by default
  },
  resources: {
    en: { translation: en },
    zh_CN: { translation: zhCN },
    zh_TW: { translation: zhTW },
    ja: { translation: ja },
  },
});

i18n.on("languageChanged", (lng) => {
  const dayjsLocaleMap: Record<string, string> = {
    en: "en",
    zh_CN: "zh-cn",
    zh_TW: "zh-tw",
    ja: "ja",
  };
  dayjs.locale(dayjsLocaleMap[lng] || "en");
});

export default i18n;
