import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { DateRangeFilter, SegmentedControl } from "@/shared/components";
import { periodLabel } from "@/features/statistics/periodLabel";
import type { ReceiptListOrder, ReceiptPeriod } from "@/stores/ReceiptStore";
import { useStores } from "@/stores/StoreContext";

/**
 * The receipts list's period (BRD F3.10): the current month by default, three months,
 * all, or days picked by hand — the preset remembered between visits.
 */
export const DateFilterModal = observer(() => {
  const { receiptStore } = useStores();
  const { t } = useTranslation(["receipts", "statistics"]);
  const [picking, setPicking] = useState(false);
  const { startDateFilter: start, endDateFilter: end } = receiptStore;
  const custom = receiptStore.period === "custom" && start && end ? ([start, end] as const) : null;
  return (
    <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row md:items-center">
      <SegmentedControl<ReceiptPeriod>
        label={t("statistics:period")}
        size="sm"
        fill
        value={receiptStore.period}
        onChange={(chosen) => {
          if (chosen === "custom") setPicking(true);
          else receiptStore.choosePeriod(chosen);
        }}
        options={[
          { value: "this_month", label: t("statistics:presets.thisMonth") },
          {
            value: "last_3_months",
            label: t("statistics:presets.last3"),
            shortLabel: t("statistics:presets.last3Short"),
          },
          { value: "all", label: t("list.allTime"), shortLabel: t("list.allTimeShort") },
          { value: "custom", label: t("statistics:presets.custom") },
        ]}
      />
      {/* Only a hand-picked period needs its days spelled out; a preset names itself. */}
      {(custom !== null || picking) && (
        <DateRangeFilter
          start={start}
          end={end}
          label={custom ? periodLabel(custom[0], custom[1]) : t("statistics:presets.custom")}
          isOpen={picking}
          onOpenChange={setPicking}
          onApply={(startDate, endDate) => {
            receiptStore.setFilters({ startDate, endDate });
          }}
        />
      )}
    </div>
  );
});

/** Purchase-date order, as the month counts, or "Recently added", as receipts arrived. */
export const ReceiptOrderControl = observer(() => {
  const { receiptStore } = useStores();
  const { t } = useTranslation("receipts");
  return (
    <SegmentedControl<ReceiptListOrder>
      label={t("list.order")}
      size="sm"
      fill
      value={receiptStore.order}
      onChange={(order) => {
        receiptStore.chooseOrder(order);
      }}
      options={[
        { value: "newest", label: t("list.byPurchase"), shortLabel: t("list.byPurchaseShort") },
        { value: "recent", label: t("list.recent"), shortLabel: t("list.recentShort") },
      ]}
    />
  );
});
