import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Card, ErrorState, LoadingState, Meter, SegmentedControl } from "@/shared/components";
import { dateFormat } from "@/i18n/format";
import type { ReportPeriod, UsageReport } from "@/stores/AnalyticsStore";
import { useStores } from "@/stores/StoreContext";

const DAY = dateFormat({ day: "numeric", month: "short", timeZone: "UTC" });

/**
 * How the service is used, for its admins (F17.3.3): visits, sign-ups, who is active and
 * who returns, the path from visit to first receipt — counts only, never anyone's data.
 * Opened inside `AdminLayout`, which keeps everyone else out.
 */
export const AdminDashboardPage = observer(function AdminDashboardPage() {
  const { analyticsStore } = useStores();
  const { t } = useTranslation("admin");
  const { report, reportState, period } = analyticsStore;

  useEffect(() => {
    void analyticsStore.loadReport();
  }, [analyticsStore]);

  return (
    <section className="flex flex-col gap-4 md:gap-6">
      <p className="m-0 text-lg text-muted-foreground">{t("subtitle")}</p>
      <SegmentedControl<ReportPeriod>
        label={t("periods.label")}
        size="sm"
        fill
        value={period}
        onChange={(chosen) => {
          analyticsStore.choosePeriod(chosen);
        }}
        options={[
          { value: "last_7", label: t("periods.last7"), shortLabel: t("periods.last7Short") },
          { value: "last_30", label: t("periods.last30"), shortLabel: t("periods.last30Short") },
          { value: "this_month", label: t("periods.thisMonth") },
        ]}
      />
      {reportState.error ? (
        <ErrorState layout="banner" title={t("failed")} message={reportState.error} />
      ) : !report ? (
        <LoadingState title={t("loading")} />
      ) : (
        <Figures report={report} />
      )}
    </section>
  );
});

function Figures({ report }: { report: UsageReport }) {
  const { t } = useTranslation("admin");
  const tiles: [string, number][] = [
    [t("tiles.visits"), report.visits],
    [t("tiles.pageViews"), report.page_views],
    [t("tiles.signUps"), report.sign_ups],
    [t("tiles.confirmed"), report.confirmed],
    [t("tiles.withReceipt"), report.with_a_receipt],
    [t("tiles.uploads"), report.uploads],
    [t("tiles.receiptsRead"), report.receipts_read],
    [t("tiles.activeWeek"), report.active_week],
    [t("tiles.activeMonth"), report.active_month],
    [t("tiles.returning"), report.returning],
  ];
  const funnel: [string, number][] = [
    [t("funnel.visits"), report.visits],
    [t("funnel.signUps"), report.sign_ups],
    [t("funnel.confirmed"), report.confirmed],
    [t("funnel.withReceipt"), report.with_a_receipt],
  ];
  const widest = Math.max(...funnel.map(([, n]) => n), 1);
  const busiest = Math.max(...report.days.map((d) => d.visits + d.sign_ups + d.receipts_read), 1);

  return (
    <>
      <dl className="m-0 grid grid-cols-2 gap-3 md:grid-cols-3">
        {tiles.map(([label, value]) => (
          <Card key={label} variant="surface" className="flex flex-col gap-1 p-3 md:p-4">
            <dt className="text-base text-muted-foreground">{label}</dt>
            <dd className="m-0 text-xl font-bold tabular-nums">{value}</dd>
          </Card>
        ))}
      </dl>

      <Card variant="surface" className="flex flex-col gap-3 p-4 md:p-5">
        <h2 className="m-0 text-lg font-semibold">{t("funnel.title")}</h2>
        <ol className="m-0 flex list-none flex-col gap-2.5 p-0">
          {funnel.map(([label, value]) => (
            <li key={label} className="flex flex-col gap-1">
              <span className="flex justify-between text-md">
                <span>{label}</span>
                <span className="tabular-nums">{value}</span>
              </span>
              <Meter value={(value / widest) * 100} />
            </li>
          ))}
        </ol>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Ranked title={t("byPage")} rows={report.views_by_page} />
        <Ranked
          title={t("bySource")}
          rows={report.visits_by_source.map((row) =>
            row.name === "direct" ? { ...row, name: t("direct") } : row,
          )}
        />
      </div>

      <Card variant="surface" className="flex flex-col gap-3 p-4 md:p-5">
        <h2 className="m-0 text-lg font-semibold">{t("byDay.title")}</h2>
        <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
          {report.days.map((day) => (
            <li key={day.day} className="flex flex-col gap-1">
              <span className="flex flex-wrap justify-between gap-x-3 text-base">
                <span className="font-medium">{DAY.format(new Date(`${day.day}T00:00:00Z`))}</span>
                <span className="tabular-nums text-muted-foreground">
                  {t("byDay.line", {
                    visits: day.visits,
                    signUps: day.sign_ups,
                    reads: day.receipts_read,
                  })}
                </span>
              </span>
              <Meter value={((day.visits + day.sign_ups + day.receipts_read) / busiest) * 100} />
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}

function Ranked({ title, rows }: { title: string; rows: { name: string; count: number }[] }) {
  const { t } = useTranslation("admin");
  return (
    <Card variant="surface" className="flex flex-col gap-3 p-4 md:p-5">
      <h2 className="m-0 text-lg font-semibold">{title}</h2>
      {rows.length === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("nothing")}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
          {rows.map((row) => (
            <li key={row.name} className="flex justify-between gap-3 text-md">
              <span className="break-all">{row.name}</span>
              <span className="tabular-nums">{row.count}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
