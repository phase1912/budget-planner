/** Each built-in category's colour token; a user's own shares `--cat-other`. */
const COLORS: Record<string, string> = {
  Groceries: "var(--cat-groceries)",
  Dining: "var(--cat-dining)",
  Transport: "var(--cat-transport)",
  Utilities: "var(--cat-utilities)",
  Health: "var(--cat-health)",
  Entertainment: "var(--cat-entertainment)",
  Other: "var(--cat-other)",
  Uncategorized: "var(--cat-uncategorised)",
};

/** A category's colour token; custom or unknown categories share `--cat-other`. */
export function categoryColor(name: string): string {
  return COLORS[name] ?? "var(--cat-other)";
}
