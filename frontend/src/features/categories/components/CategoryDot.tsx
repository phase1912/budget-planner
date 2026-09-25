import { categoryColor } from "./categoryColor";

interface CategoryDotProps {
  name: string;
}

/**
 * Category color dot matching the design system's `--cat-*` tokens.
 *
 * Maps a category name to its CSS variable. Custom or unknown categories
 * fall back to `--cat-other`.
 */
export function CategoryDot({ name }: CategoryDotProps) {
  const color = categoryColor(name);
  return (
    <span
      className="inline-block w-[10px] h-[10px] rounded-full shrink-0"
      style={{ background: color }}
      aria-hidden="true"
    />
  );
}
