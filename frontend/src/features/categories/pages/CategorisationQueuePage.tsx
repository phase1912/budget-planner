import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";
import { CheckCircle2, SlidersHorizontal } from "lucide-react";

import { useStores } from "@/stores/StoreContext";
import {
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Pill,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components";
import type { ReviewQueueItem } from "@/stores/CategoriesStore";

const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

function purchaseDate(item: ReviewQueueItem): string {
  return item.transaction_date ? DATE_FORMAT.format(new Date(item.transaction_date)) : "—";
}

/**
 * The categorisation review queue: items the agent filed under Uncategorized
 * because it was not confident, oldest purchase first (BRD C2, C3 — F5.3).
 *
 * Read-only until F5.4 adds the inline category picker and the "Corrected by
 * you" / "All items" views shown in docs/design/screens/categorisation.html.
 */
export const CategorisationQueuePage = observer(function CategorisationQueuePage() {
  const { categoriesStore } = useStores();
  const { reviewQueue, isLoadingQueue, queueError } = categoriesStore;

  useEffect(() => {
    void categoriesStore.fetchReviewQueue();
  }, [categoriesStore]);

  return (
    <div className="flex-grow flex flex-col items-center py-10 px-4 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-6">
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[28px] font-bold tracking-[-0.02em] text-foreground">
              Categories
            </h1>
            <p className="m-0 text-lg text-muted-foreground">
              Items the agent was not confident about, oldest first.
            </p>
          </div>
          <Link
            to="/categories/manage"
            className="inline-flex items-center gap-2 text-lg font-semibold text-primary hover:text-primary-hover"
          >
            <SlidersHorizontal size={16} aria-hidden="true" />
            Manage the taxonomy
          </Link>
        </header>

        {isLoadingQueue ? (
          <LoadingState title="Loading the review queue…" />
        ) : queueError ? (
          <ErrorState
            layout="banner"
            title="The review queue could not be loaded"
            message={queueError}
          />
        ) : reviewQueue.length === 0 ? (
          <Card className="py-12 px-6">
            <EmptyState
              icon={CheckCircle2}
              iconTone="primary"
              title="Nothing needs review"
              message="Every item the agent has seen was placed with confidence."
            />
          </Card>
        ) : (
          <Card flush>
            <Table>
              <TableHeader className="bg-surface">
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead>Merchant</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Category</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reviewQueue.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-semibold">{item.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {item.merchant_name ?? "—"}
                    </TableCell>
                    <TableCell className="tabular-nums text-muted-foreground whitespace-nowrap">
                      {purchaseDate(item)}
                    </TableCell>
                    <TableCell className="tabular-nums text-right font-semibold">
                      {Number(item.total_price).toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <Pill tone="warning" size="sm">
                        {item.category?.name ?? "Uncategorized"}
                      </Pill>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}
      </div>
    </div>
  );
});
