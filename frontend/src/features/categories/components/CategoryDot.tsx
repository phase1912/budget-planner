/**
 * Category color dot matching the design system's `--cat-*` tokens.
 *
 * Maps a category name to its CSS variable. Custom or unknown categories
 * fall back to `--cat-other`.
 */

const CATEGORY_COLOR_MAP: Record<string, string> = {
  Groceries: "var(--cat-groceries)",
  Dining: "var(--cat-dining)",
  Transport: "var(--cat-transport)",
  Utilities: "var(--cat-utilities)",
  Health: "var(--cat-health)",
  Entertainment: "var(--cat-entertainment)",
  Other: "var(--cat-other)",
  Uncategorized: "var(--cat-uncategorised)",
};

interface CategoryDotProps {
  name: string;
}

export function CategoryDot({ name }: CategoryDotProps) {
  const color = CATEGORY_COLOR_MAP[name] ?? "var(--cat-other)";
  return (
    <span
      className="inline-block w-[10px] h-[10px] rounded-full shrink-0"
      style={{ background: color }}
      aria-hidden="true"
    />
  );
}
