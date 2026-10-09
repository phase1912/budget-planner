import { observer } from "mobx-react-lite";

import { Meter } from "@/shared/components";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";

const DAY = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long" });

/**
 * This month's receipt reads against the account's limit (BRD F10 — F10.6): photos and
 * forwarded e-receipts alike, since each is read by the model. An admin has no limit.
 */
export const ReceiptUsageCard = observer(function ReceiptUsageCard() {
  const { quotaStore } = useStores();
  const quota = quotaStore.quota;
  if (!quota) return null;

  return (
    <Card variant="surface" flush>
      <CardHeader>Receipts this month</CardHeader>
      <CardBody className="flex flex-col gap-3">
        {quota.unlimited || quota.limit === null ? (
          <p className="m-0 text-md text-muted-foreground">
            No limit on this account. {quota.used} read so far this month.
          </p>
        ) : (
          <>
            <p className="m-0 text-lg font-semibold tabular-nums">
              {quota.used} of {quota.limit} read
            </p>
            <Meter value={(quota.used / Math.max(quota.limit, 1)) * 100} />
            <p className="m-0 text-md text-muted-foreground">
              Each receipt read by photo or by email counts. The count starts again on{" "}
              {DAY.format(new Date(`${quota.resets_on}T00:00:00`))}.
            </p>
          </>
        )}
      </CardBody>
    </Card>
  );
});
