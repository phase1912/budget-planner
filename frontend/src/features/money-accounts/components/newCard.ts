import { useTranslation } from "react-i18next";

export interface NewCard {
  name: string;
  opening: string;
}

/** The card as the API takes it: the amount typed with a comma or spaces, or none. */
export function newCardBody(card: NewCard): { name: string; opening: string } | null {
  const opening = card.opening.trim().replace(",", ".").replace(/\s/g, "") || "0";
  if (!card.name.trim() || !/^-?\d+(\.\d{1,2})?$/.test(opening)) return null;
  return { name: card.name.trim(), opening };
}

/** The name a new card starts with: "My card", or "Our card" for the family's. */
export function useCardName(): (shared: boolean) => string {
  const { t } = useTranslation("accounts");
  return (shared) => (shared ? t("newCard.defaultShared") : t("newCard.defaultName"));
}
