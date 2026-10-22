import type { Goal } from "@/stores/GoalsStore";

/** The categories and products a goal watches, by the names the user reads (F8.2). */
export function watchedLines(goal: Goal, categoryName: (id: string) => string | null): string[] {
  return [
    ...goal.mapped_category_ids.map((id) => categoryName(id)).filter((n): n is string => !!n),
    ...goal.mapped_item_names,
  ];
}
