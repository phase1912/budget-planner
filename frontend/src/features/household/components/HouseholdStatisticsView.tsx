import { useEffect } from "react";
import { observer } from "mobx-react-lite";

import { Card, ErrorState, LoadingState, Meter } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * The household's spend by category on Statistics (F12.5, ADR-0017, BRD E1): the shared
 * receipts' categories, ranked, and everyone's private spending as a single row, so
 * nothing in it says what was bought. A member's own category names its owner.
 */
export const HouseholdStatisticsView = observer(function HouseholdStatisticsView({
  start,
  end,
  currency,
}: {
  start: string;
  end: string;
  currency: string;
}) {
  const { householdStore } = useStores();
  const stats = householdStore.statistics;
  const { error, isLoading } = householdStore.statisticsState;
  const members = householdStore.household?.members ?? [];

  useEffect(() => {
    void householdStore.loadStatistics(start, end);
  }, [householdStore, start, end]);

  if (!stats) {
    return error ? (
      <ErrorState
        layout="banner"
        title="The household's statistics could not be loaded"
        message={error}
      />
    ) : (
      <LoadingState title="Loading the household's statistics…" />
    );
  }

  if (Number(stats.total) === 0) {
    return (
      <Card variant="surface" className="p-5 text-muted-foreground md:px-8">
        No receipts from anyone in the household in this period.
      </Card>
    );
  }

  const ownerName = (ownerId: string | null) =>
    ownerId ? members.find((m) => m.user_id === ownerId)?.first_name : undefined;
  const rows = [
    ...stats.categories.map((c) => ({
      key: c.category_id ?? "none",
      name: c.name ?? "Uncategorized",
      owner: ownerName(c.owner_id),
      total: Number(c.total),
      share: Number(c.share),
    })),
    ...(Number(stats.private_total) > 0
      ? [
          {
            key: "private",
            name: "Private",
            owner: undefined,
            total: Number(stats.private_total),
            share: Number(stats.private_share),
          },
        ]
      : []),
  ];

  return (
    <Card
      variant="surface"
      aria-busy={isLoading}
      className={`flex flex-col gap-4 p-5 md:px-8 md:py-6 transition-opacity ${isLoading ? "opacity-60" : ""}`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="m-0 text-lg font-semibold">Spent together</h2>
        <span className="tabular-nums font-semibold">
          {AMOUNT.format(Number(stats.total))} {currency}
        </span>
      </div>
      <ul className="m-0 flex list-none flex-col gap-4 p-0">
        {rows.map((row) => (
          <li key={row.key} className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 truncate font-semibold">
                {row.name}
                {row.owner && (
                  <span className="ml-2 text-md font-normal text-muted-foreground">
                    {row.owner}&apos;s
                  </span>
                )}
              </span>
              <span className="shrink-0 tabular-nums">
                {AMOUNT.format(row.total)}
                <span className="ml-2 text-md text-muted-foreground">{row.share}%</span>
              </span>
            </div>
            <Meter value={row.share} />
          </li>
        ))}
      </ul>
      {Number(stats.private_total) > 0 && (
        <p className="m-0 text-sm text-muted-foreground">
          Private is everyone&apos;s receipts marked private, added up: only the amount is shared.
        </p>
      )}
    </Card>
  );
});
