import { observer } from "mobx-react-lite";

import { Meter } from "@/shared/components";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";
import { dateFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const DAY = dateFormat({ day: "numeric", month: "long" });

/**
 * This month's receipt reads against the account's limit (BRD F10 — F10.6): photos and
 * forwarded e-receipts alike, since each is read by the model. An admin has no limit.
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
        {quota.unlimited || quota.limit === null ? (
          <p className="m-0 text-md text-muted-foreground">
            {t("usage.unlimited", { used: quota.used })}
          </p>
        ) : (
          <>
            <p className="m-0 text-lg font-semibold tabular-nums">
              {t("usage.used", { used: quota.used, limit: quota.limit })}
            </p>
            <Meter value={(quota.used / Math.max(quota.limit, 1)) * 100} />
            <p className="m-0 text-md text-muted-foreground">
              {t("usage.note", { date: DAY.format(new Date(`${quota.resets_on}T00:00:00`)) })}
            </p>
          </>
        )}
      </CardBody>
    </Card>
  );
});
