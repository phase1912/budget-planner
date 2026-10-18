import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { CategoryIcon } from "@/shared/components";
import { categoryColor } from "@/shared/categoryColor";
import { categoryName } from "@/shared/categoryName";
import { numberFormat } from "@/i18n/format";
import type { CategorySpend } from "@/stores/CategoriesStore";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const SHOWN = 4;

interface CategoryTilesProps {
  spend: CategorySpend[];
  hrefFor: (categoryId: string) => string;
}

/**
 * "Where it went" on Home (F23.3): the biggest categories as coloured tiles — the
 * palette's colour and picture for each, its amount and its share of the month — and
 * the way into Spending for the rest.
 */
export function CategoryTiles({ spend, hrefFor }: CategoryTilesProps) {
  const { t } = useTranslation("dashboard");
  if (spend.length === 0) return null;
  const overall = spend.reduce((sum, c) => sum + Number(c.total_amount), 0);
  return (
    <section aria-labelledby="where-it-went" className="flex flex-col gap-2.5">
      <div className="flex items-baseline justify-between">
        <h2 id="where-it-went" className="m-0 text-xl font-extrabold">
          {t("top.title")}
        </h2>
        <Link
          to="/spending"
          className="text-md font-bold text-primary"
          aria-label={t("top.allLabel")}
        >
          {t("top.all")}
        </Link>
      </div>
      <ul className="m-0 grid list-none grid-cols-2 gap-2.5 p-0 md:grid-cols-4">
        {spend.slice(0, SHOWN).map((category) => {
          const amount = Number(category.total_amount);
          const share = overall > 0 ? (amount / overall) * 100 : 0;
          const color = categoryColor(category.name ?? "");
          const body = (
            <>
              <CategoryIcon name={category.name ?? ""} size="lg" />
              <span className="flex flex-col gap-0.5">
                <span className="truncate text-base font-semibold text-muted-foreground">
                  {categoryName(category.name)}
                </span>
                <span className="text-xl font-extrabold tabular-nums">{WHOLE.format(amount)}</span>
              </span>
              <span className="h-1.5 overflow-hidden rounded-pill bg-muted" aria-hidden="true">
                <span
                  className="block h-1.5 rounded-pill"
                  style={{ width: `${String(share)}%`, background: color }}
                />
              </span>
            </>
          );
          const tile = "flex h-full flex-col gap-2.5 rounded-card bg-surface p-3.5 text-foreground";
          return (
            <li key={category.category_id ?? "none"}>
              {category.category_id ? (
                <Link to={hrefFor(category.category_id)} className={tile}>
                  {body}
                </Link>
              ) : (
                <div className={tile}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
