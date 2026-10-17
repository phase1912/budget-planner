import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Card, ErrorState, LoadingState } from "@/shared/components";
import { dateFormat } from "@/i18n/format";
import type { AdminLogEntry } from "@/stores/AdminStore";
import { useStores } from "@/stores/StoreContext";
import { NotFoundPage } from "@/features/public-landing/pages/NotFoundPage";

const MOMENT = dateFormat({
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** What admins did, newest first: read by super admins only (F18.6.3). */
export const AdminLogPage = observer(function AdminLogPage() {
  const { adminStore, authStore } = useStores();
  const { t } = useTranslation("admin");
  const isSuper = authStore.user?.is_super_admin === true;
  const { log, logState } = adminStore;

  useEffect(() => {
    if (isSuper) void adminStore.loadLog();
  }, [adminStore, isSuper]);

  if (!isSuper) return <NotFoundPage />;
  if (logState.error)
    return <ErrorState layout="banner" title={t("failed")} message={logState.error} />;
  if (logState.isLoading && log.length === 0) return <LoadingState title={t("log.loading")} />;
  if (log.length === 0)
    return <p className="m-0 text-md text-muted-foreground">{t("log.empty")}</p>;

  return (
    <Card variant="surface" flush>
      <ol className="m-0 flex list-none flex-col divide-y divide-border p-0">
        {log.map((entry) => (
          <Entry key={entry.id} entry={entry} />
        ))}
      </ol>
    </Card>
  );
});

function Entry({ entry }: { entry: AdminLogEntry }) {
  const { t } = useTranslation("admin");
  const reason = typeof entry.details.reason === "string" ? entry.details.reason : null;
  const days = typeof entry.details.days === "number" ? entry.details.days : null;
  return (
    <li className="flex flex-col gap-1 px-4 py-3">
      <span className="flex flex-wrap justify-between gap-x-3">
        <span className="font-semibold">
          {t(`log.actions.${entry.action}` as "log.actions.plan_granted", entry.action)}
        </span>
        <span className="tabular-nums text-base text-muted-foreground">
          {MOMENT.format(new Date(entry.created_at))}
        </span>
      </span>
      <span className="break-all text-base text-muted-foreground">
        {t("log.line", {
          admin: entry.admin ?? t("log.gone"),
          target: entry.target ?? t("log.gone"),
        })}
      </span>
      {(reason ?? days) !== null && (
        <span className="text-base text-muted-foreground">
          {[
            days !== null ? t("log.days", { count: days }) : null,
            reason ? t("log.reason", { reason }) : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
      )}
    </li>
  );
}
