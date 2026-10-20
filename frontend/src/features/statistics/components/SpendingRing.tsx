import { useState } from "react";
import { useTranslation } from "react-i18next";

import { House } from "lucide-react";

import { CategoryIcon, Ring } from "@/shared/components";
import { categoryColor } from "@/shared/categoryColor";
import { categoryName } from "@/shared/categoryName";
import { numberFormat } from "@/i18n/format";
import type { CategoryStatistics } from "@/stores/StatisticsStore";
import { Change } from "./Change";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const SHARE = numberFormat({ style: "percent", maximumFractionDigits: 0 });

interface SpendingRingProps {
  statistics: CategoryStatistics;
  currency: string;
}

/**
 * The period's spending as a ring by category (F23.4): tap a category and the ring
 * lights it, its amount and share in the middle; tap again or the ring for the whole.
 * With the comparison on, each row says how it moved against the previous period (E3).
 * Regular bills are spending too (F23.21): their own segment and row, beside the
 * categories rather than one of them, and part of the whole.
 */
export function SpendingRing({ statistics, currency }: SpendingRingProps) {
  const { t } = useTranslation("statistics");
  const [picked, setPicked] = useState<number | null>(null);
  const categories = statistics.categories;
  const bills = Number(statistics.bills_total);
  const total = Number(statistics.total ?? 0) + bills;
  const chosen = picked === null ? null : categories[picked];

  return (
    <section
      aria-label={t("ring.label")}
      className="flex flex-col items-center gap-5 rounded-hero bg-surface p-5 md:flex-row md:items-start md:gap-8 md:p-7"
    >
      <button
        type="button"
        onClick={() => {
          setPicked(null);
        }}
        aria-label={t("ring.showAll")}
        className="rounded-pill"
      >
        <Ring
          className="h-52 w-52 md:h-60 md:w-60"
          thickness={0.3}
          label={t("ring.picture", { total: WHOLE.format(total), currency })}
          segments={[
            ...categories.map((c, i) => ({
              value: Number(c.total),
              color:
                picked === null || picked === i
                  ? categoryColor(c.name ?? "")
                  : `color-mix(in srgb, ${categoryColor(c.name ?? "")} 25%, transparent)`,
            })),
            {
              value: bills,
              color:
                picked === null
                  ? "var(--cat-utilities)"
                  : "color-mix(in srgb, var(--cat-utilities) 25%, transparent)",
            },
          ]}
        >
          <span className="max-w-[8rem] truncate text-base font-semibold text-muted-foreground">
            {chosen ? categoryName(chosen.name) : t("ring.spent")}
          </span>
          <span className="text-[28px] font-bold leading-tight tabular-nums">
            {WHOLE.format(chosen ? Number(chosen.total) : total)}
          </span>
          <span className="text-sm text-muted-foreground">
            {chosen ? SHARE.format(Number(chosen.share) / 100) : currency}
          </span>
        </Ring>
      </button>
      <ul className="m-0 flex w-full list-none flex-col gap-1 p-0">
        {categories.map((category, i) => {
          const on = picked === i;
          return (
            <li key={category.category_id ?? "none"}>
              <button
                type="button"
                aria-pressed={on}
                onClick={() => {
                  setPicked(on ? null : i);
                }}
                className={`flex min-h-13 w-full items-center gap-3 rounded-control px-2.5 py-1.5 text-left transition-[background,opacity] ${
                  on ? "bg-tone-primary-bg" : ""
                } ${picked !== null && !on ? "opacity-55" : ""}`}
              >
                <CategoryIcon name={category.name ?? ""} size="md" />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-lg font-semibold">
                    {categoryName(category.name)}
                  </span>
                  {category.change != null && (
                    <span className="text-sm">
                      <Change change={category.change} percent={category.change_percent} compact />
                    </span>
                  )}
                </span>
                <span className="flex flex-col items-end">
                  <span className="text-lg font-bold tabular-nums">
                    {WHOLE.format(Number(category.total))}
                  </span>
                  <span className="text-sm text-muted-foreground tabular-nums">
                    {SHARE.format(Number(category.share) / 100)}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
        {bills > 0 && (
          <li className="flex min-h-13 items-center gap-3 px-2.5 py-1.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-muted text-muted-foreground">
              <House size={18} aria-hidden="true" />
            </span>
            <span className="flex-1 truncate text-lg font-semibold">{t("ring.bills")}</span>
            <span className="text-lg font-bold tabular-nums">{WHOLE.format(bills)}</span>
          </li>
        )}
      </ul>
    </section>
  );
}
