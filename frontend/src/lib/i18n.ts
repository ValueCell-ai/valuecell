import dayjs from "dayjs";
import "dayjs/locale/en";
import "dayjs/locale/en-gb";
import "dayjs/locale/ja";
import "dayjs/locale/zh-cn";
import "dayjs/locale/zh-tw";
import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import Backend from "i18next-http-backend";
import { initReactI18next } from "react-i18next";

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "en-US",
    debug: import.meta.env.DEV,
    interpolation: {
      escapeValue: false, // not needed for react as it escapes by default
    },
    backend: {
      loadPath: "/locales/{{lng}}/translation.json",
    },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "valuecell-settings", // We might need to parse this if it's a JSON string from zustand persist
      // Actually, zustand persist stores it as a JSON string with `state` key.
      // i18next-browser-languagedetector by default looks for a simple string.
      // So we might need a custom detector or just rely on our store syncing.
      // Let's rely on manual sync for now: Initialize with store value, and change when store changes.
      // Or just disable detection and control it via store.
      // But user might want auto-detection on first load if no store value.
      // Let's stick to standard detection for now, but priority is manual control.
      caches: [], // Don't cache in localStorage by i18next, we use our own store.
    },
  });

i18n.on("languageChanged", (lng) => {
  const dayjsLocaleMap: Record<string, string> = {
    "en-US": "en",
    "en-GB": "en-gb",
    "zh-Hans": "zh-cn",
    "zh-Hant": "zh-tw",
    "ja-JP": "ja",
  };
  dayjs.locale(dayjsLocaleMap[lng] || "en");
});

export default i18n;
