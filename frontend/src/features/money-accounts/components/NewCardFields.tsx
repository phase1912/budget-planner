import { useTranslation } from "react-i18next";

import { Input } from "@/shared/components";
import type { NewCard } from "./newCard";

/**
 * Where income lands when there is no card yet (F23.21): income is bookkeeping, so adding
 * the first one makes the card in the same step — its name and, if the user knows it,
 * what is on it now. Left empty, the card counts from this income on.
 */
export function NewCardFields({
  value,
  onChange,
  currency,
}: {
  value: NewCard;
  onChange: (value: NewCard) => void;
  currency: string;
}) {
  const { t } = useTranslation("accounts");
  return (
    <fieldset className="m-0 flex flex-col gap-3 rounded-card border-0 bg-tone-primary-bg p-3.5">
      <legend className="sr-only">{t("newCard.title")}</legend>
      <p className="m-0 text-md font-bold">{t("newCard.title")}</p>
      <p className="m-0 text-md leading-relaxed text-muted-foreground">{t("newCard.hint")}</p>
      <Input
        label={t("newCard.name")}
        maxLength={80}
        value={value.name}
        onChange={(e) => {
          onChange({ ...value, name: e.target.value });
        }}
      />
      <Input
        label={t("newCard.opening", { currency })}
        inputMode="decimal"
        placeholder="0"
        value={value.opening}
        onChange={(e) => {
          onChange({ ...value, opening: e.target.value });
        }}
      />
    </fieldset>
  );
}
