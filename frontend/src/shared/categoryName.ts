import i18n from "@/i18n";

/** The built-in categories, by the English names the server stores them under (BRD C1). */
const BUILT_IN = new Set([
  "Groceries",
  "Dining",
  "Transport",
  "Utilities",
  "Health",
  "Entertainment",
  "Other",
  "Uncategorized",
]);

/**
 * A category as the user reads it (F9.9): a built-in one in the app's language, one the
 * user created exactly as they named it. No user category can share a built-in's name
 * (domain model 14a), so the name alone says which it is. Colours still go by the
 * stored name, never this one.
 */
export function categoryName(name: string | null | undefined): string {
  if (!name) return i18n.t("categories:noCategory");
  return BUILT_IN.has(name)
    ? i18n.t(`categories:builtIn.${name}` as "categories:noCategory")
    : name;
}
