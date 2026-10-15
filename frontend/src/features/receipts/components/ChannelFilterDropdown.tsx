import { observer } from "mobx-react-lite";

import type { components } from "@/api/schema";
import { useStores } from "@/stores/StoreContext";
import { FilterDropdown, type FilterOption } from "./FilterDropdown";
import { useTranslation } from "react-i18next";

type ReceiptChannel = components["schemas"]["ReceiptChannel"];

// QR joins the list when QR intake exists (F11.3); a filter that can only ever
// come back empty is noise.
const CHANNELS = [
  { value: undefined, label: "filter.anySource" },
  { value: "photo", label: "filter.photo" },
  { value: "email", label: "filter.email" },
  { value: "manual", label: "filter.manual" },
] as const;

/** Narrow Receipts to those that arrived one way (BRD F11 — F11.2). */
export const ChannelFilterDropdown = observer(function ChannelFilterDropdown() {
  const { receiptStore } = useStores();
  const { t } = useTranslation("receipts");
  const options: FilterOption<ReceiptChannel>[] = CHANNELS.map((c) => ({
    value: c.value,
    label: t(c.label),
  }));
  return (
    <FilterDropdown
      label={t("filter.source")}
      options={options}
      value={receiptStore.channelFilter}
      onChange={(channel) => {
        receiptStore.setFilters({ channel });
      }}
    />
  );
});
