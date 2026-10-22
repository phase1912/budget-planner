import { observer } from "mobx-react-lite";

import { Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { dateFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const DAY = dateFormat({ day: "numeric", month: "long" });

/**
 * About how many receipts this month's AI credits still read, against what the upload
 * would need (F10.6, F21.9). Past them it says when they renew, which is why the upload
 * button beside it is held.
 */
export const ReceiptQuotaNote = observer(function ReceiptQuotaNote({ needed }: { needed: number }) {
  const { quotaStore } = useStores();
  const { t } = useTranslation("upload");
  const quota = quotaStore.quota;
  if (!quota) return null;

  if (quota.unlimited) {
    return <p className="m-0 text-md text-muted-foreground">{t("quota.unlimited")}</p>;
  }

  const left = quota.receipts_left ?? 0;
  const resets = DAY.format(new Date(`${quota.resets_on}T00:00:00`));
  if (quotaStore.allows(needed)) {
    return (
      <p className="m-0 text-md text-muted-foreground tabular-nums">
        {t("quota.left", { receipts: left, messages: quota.messages_left ?? 0 })}
      </p>
    );
  }
  return (
    <Note tone="warning">
      {left === 0
        ? t("quota.used", { resets })
        : t("quota.short", { count: left, needed, extra: needed - left, resets })}
    </Note>
  );
});
