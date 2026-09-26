import { observer } from "mobx-react-lite";

import { Card } from "@/shared/components";
import type { CategorySpend } from "@/stores/CategoriesStore";
import { CategoryDot } from "./CategoryDot";
import { categoryColor } from "./categoryColor";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

interface CategorySpendListProps {
  spend: CategorySpend[];
  /** The category the list is narrowed to, marked as pressed; none on the dashboard. */
  selectedId?: string | null;
  onSelect: (categoryId: string | null) => void;
  /** The note beside the heading; defaults to the categories screen's filter hint. */
  hint?: string;
}

/**
 * Where the money in the current selection went, per category, highest first.
 *
 * The dashboard's "Where it went" (docs/design/screens/dashboard.html), also used
 * on the categories screen. There each row filters the list below it to that
 * category, and pressing it again clears the filter; on the dashboard a row opens
 * that category's items for the month. Items with no category at all are shown
 * but cannot be picked.
 */
export const CategorySpendList = observer(function CategorySpendList({
  spend,
  selectedId = null,
  onSelect,
  hint,
}: CategorySpendListProps) {
  if (spend.length === 0) return null;
  const largest = Math.max(...spend.map((c) => Number(c.total_amount)), 0);
  const overall = spend.reduce((sum, c) => sum + Number(c.total_amount), 0);

  return (
    <Card className="flex flex-col gap-3 px-4.5 py-4 md:px-6 md:py-5.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
        <h2 className="m-0 text-[16px] font-bold">Where it went</h2>
        <span className="text-base text-muted-foreground">
          {hint ?? (selectedId ? "Showing one category" : "Highest first · pick one to filter")}
        </span>
      </div>
      <ul className="m-0 p-0 list-none flex flex-col gap-0.5">
        {spend.map((category) => {
          const amount = Number(category.total_amount);
          const name = category.name ?? "No category";
          const selected = category.category_id !== null && category.category_id === selectedId;
          const share = overall > 0 ? Math.round((amount / overall) * 100) : 0;
          return (
            <li key={category.category_id ?? "none"}>
              <button
                type="button"
                aria-pressed={selected}
                disabled={category.category_id === null}
                onClick={() => {
                  onSelect(selected ? null : category.category_id);
                }}
                className={`grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 rounded-chip px-2.5 py-2 text-left transition-colors md:grid-cols-[132px_minmax(0,1fr)_104px_52px] md:gap-x-3.5 ${
                  selected ? "bg-tone-primary-bg" : "hover:bg-muted disabled:hover:bg-transparent"
                } cursor-pointer disabled:cursor-default`}
              >
                <span className="flex min-w-0 items-center gap-2.5 text-md font-semibold">
                  <CategoryDot name={name} />
                  <span className="truncate">{name}</span>
                </span>
                <span className="col-span-2 row-start-2 block h-2 rounded-[4px] bg-muted md:col-span-1 md:row-start-auto">
                  <span
                    className="block h-full rounded-[inherit]"
                    style={{
                      // A category made of discounts sums below zero; it gets no bar
                      // rather than a negative width, which CSS would draw as full.
                      width: `${String(largest > 0 ? Math.max(0, (amount / largest) * 100) : 0)}%`,
                      background: categoryColor(name),
                    }}
                  />
                </span>
                <span className="col-start-2 row-start-1 tabular-nums text-right text-md font-semibold md:col-start-auto md:row-start-auto">
                  {AMOUNT.format(amount)}
                </span>
                <span className="hidden tabular-nums text-right text-base text-muted-foreground md:block">
                  {share}%
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
});
