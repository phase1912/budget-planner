import { useEffect, useState } from "react";
import { CalendarX } from "lucide-react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";

import { CategoryDot } from "@/features/categories/components/CategoryDot";
import { ExportMenu } from "@/features/exports/components/ExportMenu";
import {
  Button,
  Card,
  DateRangeFilter,
  EmptyState,
  ErrorState,
  LoadingState,
  Note,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  SegmentedControl,
} from "@/shared/components";
import type { Preset } from "@/stores/StatisticsStore";
import { useStores } from "@/stores/StoreContext";
import { CategoryChart } from "../components/CategoryChart";
import { Change } from "../components/Change";
import { likeForLikeNote, periodLabel, periodName } from "../periodLabel";
import { HouseholdStatisticsView } from "@/features/household/components/HouseholdStatisticsView";
import { HouseholdViewSwitch } from "@/features/household/components/HouseholdViewSwitch";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
/**
 * Statistics (docs/design/screens/statistics.html): every category's total, share
 * of the period's spend and item count, biggest first (BRD E1, E4 — F7.1), over
 * this month so far, a preset, or any run of days the user picks (E2 — F7.2),
 * optionally against the previous like-for-like period (E3 — F7.3). Items on
 * receipts under review are named above the table rather than silently left out
 * (D3). A period holding no receipts says so rather than showing a table of
 * zeroes (E5 — F7.4). Above the table, the same figures as a chart, both periods
 * side by side when compared (E6 — F7.5), and exported as CSV or JSON with the
 * same figures (N6 — F7.6).
 */
export const StatisticsPage = observer(function StatisticsPage() {
  const { statisticsStore, authStore, exportStore, householdStore } = useStores();
  // The household's figures replace the user's own; the period controls serve both (F12.5).
  const household = householdStore.showingHousehold;
  const { statistics, isLoading, error, start, end, preset, compare } = statisticsStore;
  const [picking, setPicking] = useState(false);
  const currency = authStore.user?.currency ?? "PLN";
  const period = periodLabel(start, end);
  const comparison = statistics?.comparison ?? null;
  const previous = comparison ? periodLabel(comparison.start, comparison.end) : null;

  useEffect(() => {
    void statisticsStore.load();
    void householdStore.load();
  }, [statisticsStore, householdStore]);

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5">
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[24px] font-bold tracking-[-0.02em] md:text-[28px]">
              Statistics
            </h1>
            <p className="m-0 text-lg text-muted-foreground">
              Category totals over any stretch of days, not just whole months.
            </p>
          </div>
          {!household && (
            <ExportMenu
              label="Export"
              busy={Boolean(exportStore.busy.statistics)}
              onExport={(format) => {
                // The file holds this period's figures, compared if the screen is (BRD N6).
                void exportStore.start({ kind: "statistics", format, start, end, compare });
              }}
            />
          )}
        </header>

        <HouseholdViewSwitch />

        <Card
          variant="surface"
          className="flex flex-col gap-3 px-3.5 py-3.5 md:flex-row md:items-center md:px-4.5"
        >
          <SegmentedControl<Preset>
            label="Period"
            size="sm"
            fill
            value={preset}
            onChange={(chosen) => {
              if (chosen === "custom") setPicking(true);
              else void statisticsStore.choosePreset(chosen);
            }}
            options={[
              { value: "this_month", label: "This month" },
              { value: "last_month", label: "Last month" },
              { value: "last_3_months", label: "Last 3 months", shortLabel: "3 months" },
              { value: "custom", label: "Custom" },
            ]}
          />
          <DateRangeFilter
            start={start}
            end={end}
            label={period}
            allowAll={false}
            isOpen={picking}
            onOpenChange={setPicking}
            onApply={(from, to) => {
              if (from && to) void statisticsStore.chooseRange(from, to);
            }}
          />
          {!household && (
            <label className="flex min-h-11 cursor-pointer items-center gap-2.25 text-md font-semibold md:ml-auto md:min-h-0">
              <input
                type="checkbox"
                className="h-4 w-4 accent-primary"
                checked={compare}
                onChange={(e) => {
                  void statisticsStore.setCompare(e.target.checked);
                }}
              />
              Compare with {previous ?? "the previous period"}
            </label>
          )}
        </Card>

        {household ? (
          <HouseholdStatisticsView start={start} end={end} currency={currency} />
        ) : (
          <>
            {statistics && statistics.receipt_count > 0 && comparison && (
              <>
                {comparison.receipt_count === 0 ? (
                  <Note tone="info">
                    No receipts in {periodName(comparison.start, comparison.end)}, so every category
                    is new against it.
                  </Note>
                ) : (
                  comparison.stops_mid_month && (
                    <Note tone="info">{likeForLikeNote({ start, end }, comparison)}</Note>
                  )
                )}
              </>
            )}

            {error && (
              <ErrorState
                layout="banner"
                title="The statistics could not be loaded"
                message={error}
              />
            )}

            {!statistics ? (
              !error && <LoadingState title="Adding up your categories…" />
            ) : statistics.receipt_count === 0 ? (
              // No receipts is not a spend of zero: no table of zeroes (BRD E5, states.html).
              <Card variant="surface" className="px-5 py-10">
                <EmptyState
                  icon={CalendarX}
                  title={`No receipts in ${periodName(start, end)}`}
                  message="Nothing was recorded for that period. This is not a zero — there is simply nothing to total."
                  action={
                    <Button
                      variant="secondary"
                      size="sm"
                      className="min-h-11 md:min-h-0"
                      onClick={() => {
                        setPicking(true);
                      }}
                    >
                      Pick another period
                    </Button>
                  }
                />
              </Card>
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
                        {statistics.excluded_count === 1 ? "is" : "are"} left out — their receipts
                        are waiting for review.
                      </span>
                      <Link to="/receipts?status=manual_review" className="shrink-0 underline">
                        Review them
                      </Link>
                    </span>
                  </Note>
                )}

                {statistics.chart && statistics.categories.length > 0 && (
                  <div className={`transition-opacity ${isLoading ? "opacity-60" : ""}`}>
                    <CategoryChart chart={statistics.chart} current={period} previous={previous} />
                  </div>
                )}

                <Card
                  flush
                  aria-busy={isLoading}
                  className={`transition-opacity ${isLoading ? "opacity-60" : ""}`}
                >
                  {statistics.categories.length === 0 ? (
                    // Receipts exist but all are held out for review, named in the note above.
                    <p className="m-0 p-5 text-md text-muted-foreground">
                      Nothing is counted in {period} until those receipts are reviewed.
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
                          {previous && (
                            <>
                              <TableHead className="hidden text-right md:table-cell">
                                {previous}
                              </TableHead>
                              <TableHead className="hidden text-right md:table-cell">
                                Change
                              </TableHead>
                            </>
                          )}
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
                                {/* A phone has no change column; the change goes under the amount. */}
                                {category.change != null && (
                                  <span className="block text-base font-normal md:hidden">
                                    <Change
                                      change={category.change}
                                      percent={category.change_percent}
                                      compact
                                    />
                                  </span>
                                )}
                              </TableCell>
                              <TableCell className="text-right tabular-nums text-muted-foreground">
                                {Number(category.share).toFixed(1)}%
                              </TableCell>
                              <TableCell className="hidden text-right tabular-nums text-muted-foreground md:table-cell">
                                {category.item_count}
                              </TableCell>
                              {category.change != null && (
                                <>
                                  <TableCell className="hidden text-right tabular-nums text-muted-foreground md:table-cell">
                                    {AMOUNT.format(Number(category.previous_total))}
                                  </TableCell>
                                  <TableCell className="hidden text-right md:table-cell">
                                    <Change
                                      change={category.change}
                                      percent={category.change_percent}
                                    />
                                  </TableCell>
                                </>
                              )}
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  )}
                </Card>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
});
