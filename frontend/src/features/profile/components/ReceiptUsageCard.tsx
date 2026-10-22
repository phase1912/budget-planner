import { observer } from "mobx-react-lite";

import { Meter, Pill } from "@/shared/components";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";
import { dateFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const DAY = dateFormat({ day: "numeric", month: "long" });

/**
 * This month's AI credits (F21.9): what reading receipts, talking and speaking to the
 * assistant and asking about goals have spent, drawn against the plan's month and told as
 * about how many receipts or messages are left — never as credits. An admin has no limit.
 * The plan the wallet comes from, and when a granted one ends, is shown above it (F18.4).
 */
export const ReceiptUsageCard = observer(function ReceiptUsageCard() {
  const { quotaStore } = useStores();
  const { t } = useTranslation("profile");
  const quota = quotaStore.quota;
  if (!quota) return null;

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("usage.title")}</CardHeader>
      <CardBody className="flex flex-col gap-3">
        <p className="m-0 flex flex-wrap items-center gap-2 text-md text-muted-foreground">
          <Pill tone={quota.plan === "paid" ? "success" : "default"} size="sm">
            {quota.plan === "paid" ? t("usage.planPaid") : t("usage.planFree")}
          </Pill>
          {quota.plan_ends_on &&
            t("usage.planEnds", {
              date: DAY.format(new Date(`${quota.plan_ends_on}T00:00:00`)),
            })}
        </p>
        {quota.unlimited || quota.limit === null ? (
          <p className="m-0 text-md text-muted-foreground">{t("usage.unlimited")}</p>
        ) : (
          <>
            <p className="m-0 text-lg font-semibold tabular-nums">
              {t("usage.left", {
                receipts: quota.receipts_left ?? 0,
                messages: quota.messages_left ?? 0,
              })}
            </p>
            <Meter value={100 - (quota.used / Math.max(quota.limit, 1)) * 100} />
            <p className="m-0 text-md text-muted-foreground">
              {t("usage.note", { date: DAY.format(new Date(`${quota.resets_on}T00:00:00`)) })}
            </p>
          </>
        )}
      </CardBody>
    </Card>
  );
});
