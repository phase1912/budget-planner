/** The palette's chart series, one per explored product in the order they were picked. */
const SERIES = [
  "var(--color-primary)",
  "var(--cat-dining)",
  "var(--cat-transport)",
  "var(--cat-utilities)",
  "var(--cat-health)",
  "var(--cat-entertainment)",
];

/** A product's colour by its place in the selection; the series repeats past six. */
export function productColour(index: number): string {
  return SERIES[Math.max(0, index) % SERIES.length] ?? "var(--color-primary)";
}
