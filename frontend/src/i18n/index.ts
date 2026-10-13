import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { initialLanguage } from "./languages";
import { resources } from "./resources";

/**
 * The product's translations (F9.9): English is the source and the fallback, so a key not
 * yet translated reads in English rather than as its key.
 */
void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage(),
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
  returnNull: false,
});

export default i18n;
