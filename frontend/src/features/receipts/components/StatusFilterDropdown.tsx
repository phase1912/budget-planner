import { observer } from "mobx-react-lite";

import type { components } from "@/api/schema";
import { useStores } from "@/stores/StoreContext";
import { FilterDropdown, type FilterOption } from "./FilterDropdown";

type ReceiptStatus = components["schemas"]["ReceiptStatus"];

// Only statuses a stored receipt can have: UPLOADED, PARSING and FAILED are
// transient job states that live in UploadJob, not in the receipts table.
const STATUSES: FilterOption<ReceiptStatus>[] = [
  { value: undefined, label: "Any status" },
  { value: "parsed", label: "Parsed" },
  { value: "manual_review", label: "Needs review" },
];

export const StatusFilterDropdown = observer(function StatusFilterDropdown() {
  const { receiptStore } = useStores();
  return (
    <FilterDropdown
      label="Status"
      options={STATUSES}
      value={receiptStore.statusFilter}
      onChange={(status) => {
        receiptStore.setFilters({ status });
      }}
    />
  );
});
