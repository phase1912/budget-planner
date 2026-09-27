import { Link } from "react-router-dom";

import { CategoryDot } from "@/features/categories/components/CategoryDot";
import type { CategorySpend } from "@/stores/CategoriesStore";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** How many categories a phone lists before "All" (docs/design/screens/dashboard-mobile.html). */
const SHOWN = 5;

interface TopCategoriesProps {
  spend: CategorySpend[];
  /** Where a category's row leads: its items for the month. */
  hrefFor: (categoryId: string) => string;
}

/**
 * "Where it went" as a phone shows it: the five biggest categories, without the
 * bars, and "All" leading to the full statistics (dashboard-mobile.html). The
 * shares are of the month's whole spend, as on the desktop breakdown.
 */
export function TopCategories({ spend, hrefFor }: TopCategoriesProps) {
  if (spend.length === 0) return null;
  const overall = spend.reduce((sum, c) => sum + Number(c.total_amount), 0);
  return (
    <section aria-labelledby="top-categories" className="flex flex-col">
      <div className="mb-1 flex items-baseline justify-between">
        <h2 id="top-categories" className="m-0 text-[15px] font-bold">
          Where it went
        </h2>
        <Link to="/statistics" className="text-md" aria-label="All statistics">
          All
        </Link>
      </div>
      <ul className="m-0 list-none p-0">
        {spend.slice(0, SHOWN).map((category) => {
          const name = category.name ?? "No category";
          const amount = Number(category.total_amount);
          const share = overall > 0 ? Math.round((amount / overall) * 100) : 0;
          const row = (
            <>
              <span className="flex min-w-0 items-center gap-2.25 text-md font-semibold">
                <CategoryDot name={name} />
                <span className="truncate">{name}</span>
              </span>
              <span className="text-right text-md font-semibold tabular-nums">
                {AMOUNT.format(amount)}
              </span>
              <span className="text-right text-base text-muted-foreground tabular-nums">
                {share}%
              </span>
            </>
          );
          const layout = "grid grid-cols-[minmax(0,1fr)_78px_40px] items-center gap-2.5 py-2.75";
          return (
            <li
              key={category.category_id ?? "none"}
              className="border-t border-muted first:border-t-0"
            >
              {category.category_id ? (
                <Link to={hrefFor(category.category_id)} className={`${layout} text-foreground`}>
                  {row}
                </Link>
              ) : (
                <div className={layout}>{row}</div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
