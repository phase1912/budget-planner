import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Card, ErrorState, LoadingState } from "@/shared/components";
import { dateFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";

const MOMENT = dateFormat({
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Assistant replies users reported, newest first, each with why and by whom (F22.4.2). */
export const AdminReportsPage = observer(function AdminReportsPage() {
  const { adminStore } = useStores();
  const { t } = useTranslation("admin");
  const { reports, reportsState } = adminStore;

  useEffect(() => {
    void adminStore.loadReports();
  }, [adminStore]);

  if (reportsState.error)
    return <ErrorState layout="banner" title={t("failed")} message={reportsState.error} />;
  if (reportsState.isLoading && reports.length === 0)
    return <LoadingState title={t("reports.loading")} />;
  if (reports.length === 0)
    return <p className="m-0 text-md text-muted-foreground">{t("reports.empty")}</p>;

  return (
    <Card variant="surface" flush>
      <ol className="m-0 flex list-none flex-col divide-y divide-border p-0">
        {reports.map((report) => (
          <li key={report.id} className="flex flex-col gap-1.5 px-4 py-3">
            <span className="flex flex-wrap justify-between gap-x-3">
              <span className="font-semibold">
                {t(`reports.reasons.${report.reason}` as "reports.reasons.other", report.reason)}
              </span>
              <span className="tabular-nums text-base text-muted-foreground">
                {MOMENT.format(new Date(report.created_at))}
              </span>
            </span>
            <p className="m-0 whitespace-pre-wrap break-words text-md">{report.reply_text}</p>
            <span className="text-base text-muted-foreground">
              {report.reporter ?? t("log.gone")}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
});
