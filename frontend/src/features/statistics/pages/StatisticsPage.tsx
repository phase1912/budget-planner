import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { CalendarDays } from "lucide-react";
import { Link } from "react-router-dom";

import { CategoryDot } from "@/features/categories/components/CategoryDot";
import {
  Card,
  ErrorState,
  LoadingState,
  Note,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { periodLabel } from "../periodLabel";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
/**
 * Statistics (docs/design/screens/statistics.html), first slice: every category's
 * total, share of the period's spend and item count, biggest first (BRD E1, E4 —
 * F7.1). The period is this month so far; picking another, comparing, the chart
 * and export arrive with F7.2-F7.6. Items on receipts under review are named
 * above the table rather than silently left out (D3).
 */
export const StatisticsPage = observer(function StatisticsPage() {
  const { statisticsStore, authStore } = useStores();
  const { statistics, isLoading, error, start, end } = statisticsStore;
  const currency = authStore.user?.currency ?? "PLN";
  const period = periodLabel(start, end);

  useEffect(() => {
    void statisticsStore.load();
  }, [statisticsStore]);

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5">
        <header className="flex flex-col gap-1">
          <h1 className="m-0 text-[24px] font-bold tracking-[-0.02em] md:text-[28px]">
            Statistics
          </h1>
          <p className="m-0 text-lg text-muted-foreground">
            Category totals over any stretch of days, not just whole months.
          </p>
        </header>

        <Card variant="surface" className="flex flex-wrap items-center gap-3 px-4.5 py-3.5">
          <span className="text-md font-semibold">This month</span>
          <span className="inline-flex items-center gap-2 tabular-nums text-md text-muted-foreground">
            <CalendarDays size={15} aria-hidden="true" />
            {period}
          </span>
        </Card>

        {error && (
          <ErrorState layout="banner" title="The statistics could not be loaded" message={error} />
        )}

        {!statistics ? (
          !error && <LoadingState title="Adding up your categories…" />
        ) : (
          <>
            {statistics.excluded_count > 0 && (
              <Note tone="warning">
                <span className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <span className="tabular-nums">
                    {statistics.excluded_count === 1
                      ? "1 item"
                      : `${String(statistics.excluded_count)} items`}{" "}
                    worth {AMOUNT.format(Number(statistics.excluded_amount))} {currency}{" "}
                    {statistics.excluded_count === 1 ? "is" : "are"} left out — their receipts are
                    waiting for review.
                  </span>
                  <Link to="/receipts?status=manual_review" className="shrink-0 underline">
                    Review them
                  </Link>
                </span>
              </Note>
            )}

            <Card
              flush
              aria-busy={isLoading}
              className={`transition-opacity ${isLoading ? "opacity-60" : ""}`}
            >
              {statistics.categories.length === 0 ? (
                <p className="m-0 p-5 text-md text-muted-foreground">
                  Nothing was spent in {period}.
                </p>
              ) : (
                <Table>
                  <caption className="sr-only">
                    Spending by category, {period}, highest first
                  </caption>
                  <TableHeader className="bg-surface">
                    <TableRow className="hover:bg-transparent">
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">
                        {/* A phone has the period right above; the column just says what it is. */}
                        <span className="md:hidden">Spent</span>
                        <span className="hidden md:inline">{period}</span>
                      </TableHead>
                      <TableHead className="text-right">Share</TableHead>
                      <TableHead className="hidden text-right md:table-cell">Items</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {statistics.categories.map((category) => {
                      const name = category.name ?? "No category";
                      return (
                        <TableRow key={category.category_id ?? "none"}>
                          <TableCell>
                            <span className="flex min-w-0 items-center gap-2.25 font-semibold">
                              <CategoryDot name={name} />
                              {category.category_id ? (
                                <Link
                                  to={`/categories?view=all&category=${encodeURIComponent(category.category_id)}&start=${start}&end=${end}`}
                                  className="truncate text-foreground"
                                >
                                  {name}
                                </Link>
                              ) : (
                                <span className="truncate">{name}</span>
                              )}
                            </span>
                            {/* A phone has no items column; the count goes under the name. */}
                            <span className="block pl-4.5 text-base tabular-nums text-muted-foreground md:hidden">
                              {category.item_count === 1
                                ? "1 item"
                                : `${String(category.item_count)} items`}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-semibold tabular-nums">
                            {AMOUNT.format(Number(category.total))}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-muted-foreground">
                            {Number(category.share).toFixed(1)}%
                          </TableCell>
                          <TableCell className="hidden text-right tabular-nums text-muted-foreground md:table-cell">
                            {category.item_count}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </Card>
          </>
        )}
      </div>
    </div>
  );
});
