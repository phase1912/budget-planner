import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Select } from "@/shared/components";
import { LANGUAGES, LANGUAGE_NAMES, isLanguage } from "@/i18n/languages";
import { useStores } from "@/stores/StoreContext";

/**
 * The language picker (F9.9). `compact` sits in the public header, before anyone has
 * signed in — an invite link, say, must be readable before registering — and shows the
 * language codes; the full one, on Profile, names each language in itself.
 */
export const LanguageSwitcher = observer(function LanguageSwitcher({
  compact = false,
}: {
  compact?: boolean;
}) {
  const { languageStore } = useStores();
  const { t } = useTranslation();
  return (
    <Select
      label={compact ? undefined : t("language.label")}
      aria-label={compact ? t("language.label") : undefined}
      value={languageStore.language}
      className={compact ? "min-h-11 px-2.5 py-1.5 text-md font-semibold md:min-h-0" : "w-full"}
      onChange={(e) => {
        if (isLanguage(e.target.value)) void languageStore.choose(e.target.value);
      }}
    >
      {LANGUAGES.map((language) => (
        <option key={language} value={language}>
          {compact ? language.toUpperCase() : LANGUAGE_NAMES[language]}
        </option>
      ))}
    </Select>
  );
});
