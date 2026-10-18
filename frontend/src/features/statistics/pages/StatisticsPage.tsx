import { CategoryIcon, Collapsible, Switch } from "@/shared/components";
import { useEffect, useState } from "react";
import { CalendarX } from "lucide-react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";

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
import { SpendingRing } from "../components/SpendingRing";
import { DailyBars } from "../components/DailyBars";
import { ItemsToFile, PeriodReceipts, RegularBills } from "../components/SpendingSections";
import { ReceiptDetailModal } from "@/features/receipts/components/ReceiptDetailModal";
import { DeleteReceiptDialog } from "@/features/receipts/components/DeleteReceiptDialog";
import { EditReceiptDialog } from "@/features/receipts/components/EditReceiptDialog";
import { isoDay } from "@/stores/StatisticsStore";
import { Change } from "../components/Change";
import { likeForLikeNote, periodLabel, periodName } from "../periodLabel";
import { HouseholdStatisticsView } from "@/features/household/components/HouseholdStatisticsView";
import { HouseholdViewSwitch } from "@/features/household/components/HouseholdViewSwitch";
import { numberFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";
import { categoryName } from "@/shared/categoryName";

const SHARE = numberFormat({
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const AMOUNT = numberFormat({
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
  const {
    statisticsStore,
    authStore,
    exportStore,
    householdStore,
    receiptStore,
    categoriesStore,
    incomeStore,
  } = useStores();
  const { t } = useTranslation("statistics");
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
    void categoriesStore.loadReviewCount();
    void incomeStore.loadBills();
  }, [statisticsStore, householdStore, categoriesStore, incomeStore]);

  return (
    <div className="flex-grow flex flex-col items-center pb-4">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5">
        <header className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-col">
            <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em]">{t("title")}</h1>
            <span className="truncate text-md font-semibold text-muted-foreground">{period}</span>
          </div>
          {!household && (
            <ExportMenu
              compact
              label={t("export")}
              busy={Boolean(exportStore.busy.statistics)}
              onExport={(format) => {
                // The file holds this period's figures, compared if the screen is (BRD N6).
                void exportStore.start({ kind: "statistics", format, start, end, compare });
              }}
            />
          )}
        </header>

        <HouseholdViewSwitch />

        <div className="flex flex-col gap-2.5">
          <SegmentedControl<Preset>
            label={t("period")}
            size="sm"
            fill
            value={preset}
            onChange={(chosen) => {
              if (chosen === "custom") setPicking(true);
              else void statisticsStore.choosePreset(chosen);
            }}
            options={[
              {
                value: "this_month",
                label: t("presets.thisMonth"),
                shortLabel: t("presets.thisMonthShort"),
              },
              {
                value: "last_month",
                label: t("presets.lastMonth"),
                shortLabel: t("presets.lastMonthShort"),
              },
              {
                value: "this_year",
                label: t("presets.year"),
                shortLabel: t("presets.yearShort"),
              },
              { value: "custom", label: t("presets.custom") },
            ]}
          />
          <div className="flex flex-col gap-1 md:flex-row md:items-center md:gap-4">
            {/* The header already names the period; the dates matter only for one's own. */}
            {(preset === "custom" || picking) && (
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
            )}
            {!household && (
              <div className="md:ml-auto md:w-80">
                <Switch
                  checked={compare}
                  onChange={(on) => {
                    void statisticsStore.setCompare(on);
                  }}
                  label={t("compareWith", { period: previous ?? t("previousPeriod") })}
                />
              </div>
            )}
          </div>
        </div>

        {household ? (
          <HouseholdStatisticsView start={start} end={end} currency={currency} />
        ) : (
          <>
            {statistics && statistics.receipt_count > 0 && comparison && (
              <>
                {comparison.receipt_count === 0 ? (
                  <Note tone="info">
                    {t("noPrevious", { period: periodName(comparison.start, comparison.end) })}
                  </Note>
                ) : (
                  comparison.stops_mid_month && (
                    <Note tone="info">{likeForLikeNote({ start, end }, comparison)}</Note>
                  )
                )}
              </>
            )}

            {error && <ErrorState layout="banner" title={t("loadFailed")} message={error} />}

            {!statistics ? (
              !error && <LoadingState title={t("loading")} />
            ) : statistics.receipt_count === 0 ? (
              // No receipts is not a spend of zero: no table of zeroes (BRD E5, states.html).
              <Card variant="surface" className="px-5 py-10">
                <EmptyState
                  icon={CalendarX}
                  title={t("empty.title", { period: periodName(start, end) })}
                  message={t("empty.message")}
                  action={
                    <Button
                      variant="secondary"
                      size="sm"
                      className="min-h-11 md:min-h-0"
                      onClick={() => {
                        setPicking(true);
                      }}
                    >
                      {t("empty.pick")}
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
                        {t("excluded", {
                          count: statistics.excluded_count,
                          amount: AMOUNT.format(Number(statistics.excluded_amount)),
                          currency,
                        })}
                      </span>
                      <Link to="/receipts?status=manual_review" className="shrink-0 underline">
                        {t("reviewThem")}
                      </Link>
                    </span>
                  </Note>
                )}

                {statistics.categories.length > 0 && (
                  <div className={`transition-opacity ${isLoading ? "opacity-60" : ""}`}>
                    <SpendingRing statistics={statistics} currency={currency} />
                  </div>
                )}

                {/* A bar a day reads up to about two months; longer runs keep the table. */}
                {statisticsStore.daily && statisticsStore.daily.days.length <= 62 && (
                  <DailyBars
                    daily={statisticsStore.daily}
                    currency={currency}
                    today={isoDay(new Date())}
                  />
                )}

                <PeriodReceipts />
                <ItemsToFile />
                <RegularBills currency={currency} />
                <Collapsible title={t("details")}>
                  <div className="flex flex-col gap-4">
                    {statistics.chart && statistics.categories.length > 0 && (
                      <div className={`transition-opacity ${isLoading ? "opacity-60" : ""}`}>
                        <CategoryChart
                          chart={statistics.chart}
                          current={period}
                          previous={previous}
                        />
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
                          {t("nothingCounted", { period })}
                        </p>
                      ) : (
                        <Table>
                          <caption className="sr-only">{t("caption", { period })}</caption>
                          <TableHeader className="bg-surface">
                            <TableRow className="hover:bg-transparent">
                              <TableHead>{t("cols.category")}</TableHead>
                              <TableHead className="text-right">
                                {/* A phone has the period right above; the column just says what it is. */}
                                <span className="md:hidden">{t("cols.spent")}</span>
                                <span className="hidden md:inline">{period}</span>
                              </TableHead>
                              <TableHead className="text-right">{t("cols.share")}</TableHead>
                              <TableHead className="hidden text-right md:table-cell">
                                {t("cols.items")}
                              </TableHead>
                              {previous && (
                                <>
                                  <TableHead className="hidden text-right md:table-cell">
                                    {previous}
                                  </TableHead>
                                  <TableHead className="hidden text-right md:table-cell">
                                    {t("cols.change")}
                                  </TableHead>
                                </>
                              )}
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {statistics.categories.map((category) => {
                              const name = categoryName(category.name);
                              return (
                                <TableRow key={category.category_id ?? "none"}>
                                  <TableCell>
                                    <span className="flex min-w-0 items-center gap-2.25 font-semibold">
                                      <CategoryIcon name={category.name ?? ""} />
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
                                      {t("items", { count: category.item_count })}
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
                                    {SHARE.format(Number(category.share) / 100)}
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
                  </div>
                </Collapsible>
              </>
            )}
          </>
        )}
        {receiptStore.selectedReceiptId && <ReceiptDetailModal />}
        <DeleteReceiptDialog />
        <EditReceiptDialog />
      </div>
    </div>
  );
});
