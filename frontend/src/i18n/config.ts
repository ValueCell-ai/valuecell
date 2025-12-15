import dayjs from "dayjs";
import "dayjs/locale/en";
import "dayjs/locale/ja";
import "dayjs/locale/zh-cn";
import "dayjs/locale/zh-tw";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enUS from "@/i18n/en-US.json";
import jaJP from "@/i18n/ja-JP.json";
import zhHans from "@/i18n/zh-Hans.json";
import zhHant from "@/i18n/zh-Hant.json";

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
    if (navLang === "zh-CN") return "zh-Hans";
    if (navLang === "zh-TW" || navLang === "zh-HK") return "zh-Hant";
    if (navLang.startsWith("ja")) return "ja-JP";
  }

  return "en-US";
};

i18n.use(initReactI18next).init({
  lng: getInitialLanguage(),
  fallbackLng: "en-US",
  debug: import.meta.env.DEV,
  interpolation: {
    escapeValue: false, // not needed for react as it escapes by default
  },
  resources: {
    "en-US": { translation: enUS },
    "zh-Hans": { translation: zhHans },
    "zh-Hant": { translation: zhHant },
    "ja-JP": { translation: jaJP },
  },
});

i18n.on("languageChanged", (lng) => {
  const dayjsLocaleMap: Record<string, string> = {
    "en-US": "en",
    "zh-Hans": "zh-cn",
    "zh-Hant": "zh-tw",
    "ja-JP": "ja",
  };
  dayjs.locale(dayjsLocaleMap[lng] || "en");
});

export default i18n;
