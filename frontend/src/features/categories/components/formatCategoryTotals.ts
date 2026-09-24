import type { Category } from "@/stores/CategoriesStore";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** "1 item" / "9 items", so a dialog never says "1 items". */
export function formatItemCount(count: number): string {
  return `${String(count)} ${count === 1 ? "item" : "items"}`;
}

/** The "9 items · 421.30 PLN" summary shown beside a category (BRD C1). */
export function formatCategoryTotals(category: Category): string {
  return `${formatItemCount(category.item_count)} · ${AMOUNT.format(Number(category.total_amount))} PLN`;
}

/** An amount as the taxonomy screen prints it, e.g. "421.30". */
export function formatCategoryAmount(category: Category): string {
  return AMOUNT.format(Number(category.total_amount));
}
