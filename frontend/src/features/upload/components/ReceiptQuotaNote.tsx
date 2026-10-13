import { observer } from "mobx-react-lite";

import { Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { dateFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const DAY = dateFormat({ day: "numeric", month: "long" });

/**
 * How many receipts this account may still have read this month, against what the
 * upload would need (BRD F10 — F10.6). Past the limit it says what the limit is and
 * when it resets, which is why the upload button beside it is held.
 */
export const ReceiptQuotaNote = observer(function ReceiptQuotaNote({ needed }: { needed: number }) {
  const { quotaStore } = useStores();
  const { t } = useTranslation("upload");
  const quota = quotaStore.quota;
  if (!quota) return null;

  if (quota.unlimited) {
    return <p className="m-0 text-md text-muted-foreground">{t("quota.unlimited")}</p>;
  }

  const left = quota.remaining ?? 0;
  const resets = DAY.format(new Date(`${quota.resets_on}T00:00:00`));
  if (quotaStore.allows(needed)) {
    return (
      <p className="m-0 text-md text-muted-foreground tabular-nums">
        {t("quota.left", { left, limit: quota.limit })}
      </p>
    );
  }
  return (
    <Note tone="warning">
      {left === 0
        ? t("quota.used", { limit: quota.limit, resets })
        : t("quota.short", { count: left, needed, extra: needed - left, resets })}
    </Note>
  );
});
