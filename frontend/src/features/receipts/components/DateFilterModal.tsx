import { observer } from "mobx-react-lite";

import { DateRangeFilter } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/** The receipts list's date filter, bound to `ReceiptStore` (BRD F3.10). */
export const DateFilterModal = observer(() => {
  const { receiptStore } = useStores();
  return (
    <DateRangeFilter
      start={receiptStore.startDateFilter}
      end={receiptStore.endDateFilter}
      onApply={(startDate, endDate) => {
        receiptStore.setFilters({ startDate, endDate });
      }}
    />
  );
});
