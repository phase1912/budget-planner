import { observer } from "mobx-react-lite";

import type { components } from "@/api/schema";
import { useStores } from "@/stores/StoreContext";
import { FilterDropdown, type FilterOption } from "./FilterDropdown";

type ReceiptChannel = components["schemas"]["ReceiptChannel"];

// QR joins the list when QR intake exists (F11.3); a filter that can only ever
// come back empty is noise.
const CHANNELS: FilterOption<ReceiptChannel>[] = [
  { value: undefined, label: "Any source" },
  { value: "photo", label: "From a photo" },
  { value: "email", label: "From email" },
];

/** Narrow Receipts to those that arrived one way (BRD F11 — F11.2). */
export const ChannelFilterDropdown = observer(function ChannelFilterDropdown() {
  const { receiptStore } = useStores();
  return (
    <FilterDropdown
      label="Source"
      options={CHANNELS}
      value={receiptStore.channelFilter}
      onChange={(channel) => {
        receiptStore.setFilters({ channel });
      }}
    />
  );
});
