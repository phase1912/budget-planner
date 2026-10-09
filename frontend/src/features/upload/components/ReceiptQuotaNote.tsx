import { observer } from "mobx-react-lite";

import { Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

const DAY = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long" });

/**
 * How many receipts this account may still have read this month, against what the
 * upload would need (BRD F10 — F10.6). Past the limit it says what the limit is and
 * when it resets, which is why the upload button beside it is held.
 */
export const ReceiptQuotaNote = observer(function ReceiptQuotaNote({ needed }: { needed: number }) {
  const { quotaStore } = useStores();
  const quota = quotaStore.quota;
  if (!quota) return null;

  if (quota.unlimited) {
    return <p className="m-0 text-md text-muted-foreground">No receipt limit on this account.</p>;
  }

  const left = quota.remaining ?? 0;
  const resets = DAY.format(new Date(`${quota.resets_on}T00:00:00`));
  if (quotaStore.allows(needed)) {
    return (
      <p className="m-0 text-md text-muted-foreground tabular-nums">
        {left} of {quota.limit} receipts left this month.
      </p>
    );
  }
  return (
    <Note tone="warning">
      {left === 0
        ? `You have used all ${String(quota.limit)} receipts this month. More can be read from ${resets}.`
        : `Only ${String(left)} receipt${left === 1 ? "" : "s"} left this month, and this upload has ${String(needed)}. Remove ${String(needed - left)} to read the rest, or wait until ${resets}.`}
    </Note>
  );
});
