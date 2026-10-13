import { observer } from "mobx-react-lite";

import type { components } from "@/api/schema";
import { useStores } from "@/stores/StoreContext";
import { FilterDropdown, type FilterOption } from "./FilterDropdown";
import { useTranslation } from "react-i18next";

type ReceiptStatus = components["schemas"]["ReceiptStatus"];

// Only statuses a stored receipt can have: UPLOADED, PARSING and FAILED are
// transient job states that live in UploadJob, not in the receipts table.
const STATUSES = [
  { value: undefined, label: "filter.anyStatus" },
  { value: "parsed", label: "filter.parsed" },
  { value: "manual_review", label: "filter.review" },
] as const;

export const StatusFilterDropdown = observer(function StatusFilterDropdown() {
  const { receiptStore } = useStores();
  const { t } = useTranslation("receipts");
  const options: FilterOption<ReceiptStatus>[] = STATUSES.map((s) => ({
    value: s.value,
    label: t(s.label),
  }));
  return (
    <FilterDropdown
      label={t("filter.status")}
      options={options}
      value={receiptStore.statusFilter}
      onChange={(status) => {
        receiptStore.setFilters({ status });
      }}
    />
  );
});
