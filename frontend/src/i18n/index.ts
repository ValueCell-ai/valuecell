import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "@/i18n/locales/en.json";
import ja from "@/i18n/locales/ja.json";
import zhCN from "@/i18n/locales/zh_CN.json";
import zhTW from "@/i18n/locales/zh_TW.json";
import { DEFAULT_LANGUAGE, useSettingsStore } from "@/store/settings-store";

const resources = Object.fromEntries(
  [
    ["en", en],
    ["ja", ja],
    ["zh_CN", zhCN],
    ["zh_TW", zhTW],
  ].map(([locale, translation]) => [locale, { translation }]),
);

i18n.use(initReactI18next).init({
  resources,
  lng: useSettingsStore.getState().language,
  fallbackLng: DEFAULT_LANGUAGE,
  debug: import.meta.env.DEV,
  interpolation: {
    escapeValue: false,
  },
  saveMissing: true,
  missingKeyHandler: (_lngs, _ns, key) => {
    console.log("🚀 ~ missing key:", key);
  },
});

export default i18n;
