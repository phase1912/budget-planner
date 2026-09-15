import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { Container, Stack } from "@/shared/components/Layout/Layout";
import { Button } from "@/shared/components/Button/Button";
import { Card } from "@/shared/components/Card/Card";

interface ExtractedLineItem {
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
  confidence?: number;
  file_id?: string | null;
}

interface PositionMatch {
  item_a_index: number;
  item_b_index: number;
  result: "same" | "different" | "not_possible";
  reason?: string | null;
}

interface ExtractedData {
  merchant_name?: string | null;
  currency?: string;
  line_items?: ExtractedLineItem[];
  file_ids?: string[];
  position_matches?: PositionMatch[];
  is_duplicate?: boolean | null;
  duplicate_resolved?: string | null;
  is_skipped?: boolean | null;
}

interface ExtractedDataPayload {
  extractions?: ExtractedData[];
}

import { useState } from "react";

export const ResolveStep = observer(function ResolveStep() {
  const [expandedMatches, setExpandedMatches] = useState<Set<string>>(new Set());
  const { uploadStore } = useStores();

  const handleBack = () => {
    uploadStore.currentStep = 2;
  };

  const payload = uploadStore.extractedData as unknown as ExtractedDataPayload | null;
  const extractions = payload?.extractions ?? [];

  if (extractions.length === 0) return null;

  let conflictsCount = 0;
  let settledCount = 0;

  // Here we'd count total conflicts. For now we just count position_matches.
  extractions.forEach((data) => {
    if (data.position_matches) {
      conflictsCount += data.position_matches.length;
      settledCount += data.position_matches.filter(
        (m) => m.result === "same" || m.result === "different",
      ).length;
    }
  });

  return (
    <Container size="narrow" className="py-9 pb-8">
      <Stack className="gap-6">
        <div className="flex items-center">
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <span className="text-[14px] font-semibold text-foreground">Photos</span>
          </span>
          <span className="grow h-[2px] rounded-[1px] bg-primary mx-4"></span>
          <button
            type="button"
            onClick={handleBack}
            className="inline-flex items-center gap-2.5 appearance-none bg-transparent border-none p-0 text-left cursor-pointer hover:opacity-80 transition-opacity"
          >
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <span className="text-[14px] font-semibold text-foreground">What we read</span>
          </button>
          <span className="grow h-[2px] rounded-[1px] bg-primary mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              3
            </span>
            <span className="text-[14px] font-semibold text-foreground">Resolve</span>
          </span>
        </div>

        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[30px] font-bold tracking-tight">
              Your call on {conflictsCount} things
            </h1>
            <p className="m-0 text-[15px] text-muted-foreground mt-1">
              Nothing is stored until this list is empty.
            </p>
          </div>
          <div className="flex flex-col items-end gap-[7px] w-[240px]">
            <span className="text-[13px] font-semibold text-muted-foreground">
              {settledCount} of {conflictsCount} settled
            </span>
            <span className="relative w-full h-[8px] bg-muted overflow-hidden rounded-pill">
              <span
                className="absolute top-0 left-0 h-full bg-primary"
                style={{
                  width:
                    String(conflictsCount > 0 ? (settledCount / conflictsCount) * 100 : 0) + "%",
                }}
              ></span>
            </span>
          </div>
        </div>

        {extractions.map((data, eIdx) => {
          if (data.is_skipped) return null;
          const matches = data.position_matches ?? [];
          const items = data.line_items ?? [];
          const merchantName = data.merchant_name ?? "Unknown merchant";

          return matches.map((match, mIdx) => {
            const itemA = items[match.item_a_index];
            const itemB = items[match.item_b_index];
            if (!itemA || !itemB) return null;

            // F4.2.2 expects us to render the conflict card
            if (match.result === "not_possible") {
              return (
                <Card key={String(eIdx) + "-" + String(mIdx)} flush>
                  <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-muted/30">
                    <div className="flex items-center gap-3">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-accent text-accent-foreground">
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polygon points="12 2 2 7 12 12 22 7 12 2" />
                          <polyline points="2 17 12 22 22 17" />
                          <polyline points="2 12 12 17 22 12" />
                        </svg>
                      </span>
                      <span className="text-[15px] font-bold">
                        "{itemA.name}" appears in both photos
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-pill bg-muted text-[12px] font-medium text-foreground">
                        {merchantName}
                      </span>
                    </div>
                    <span className="text-[13px] font-semibold text-muted-foreground">
                      {mIdx + 1} of {conflictsCount}
                    </span>
                  </div>

                  <div className="p-4 md:p-[18px]">
                    <div className="flex items-start gap-3 w-full p-3.5 border border-tone-error-border bg-tone-error-bg text-tone-error-prose rounded-control">
                      <svg
                        className="shrink-0 text-tone-error-text mt-[1px]"
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M18 6 6 18" />
                        <path d="m6 6 12 12" />
                      </svg>
                      <div className="flex flex-col gap-1">
                        <span className="text-[13px] font-bold text-foreground">
                          Comparison not possible
                        </span>
                        <span className="text-[12px] leading-relaxed">
                          {match.reason ??
                            "Overlap checking is skipped rather than guessed. Retake that frame and it runs again."}
                        </span>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            }

            const matchKey = String(eIdx) + "-" + String(mIdx);
            const isExpanded = expandedMatches.has(matchKey);

            if (!isExpanded) {
              return (
                <Card key={matchKey} variant="surface" flush>
                  <div className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-tone-success-bg text-tone-success-text">
                        <svg
                          width="15"
                          height="15"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      </span>
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[15px] font-bold text-muted-foreground">
                          "{itemA.name}" kept as{" "}
                          {match.result === "same" ? "one purchase" : "two purchases"}
                        </span>
                        <span className="text-[13px] font-semibold text-muted-foreground">
                          {match.result === "same"
                            ? "Counted once in the total."
                            : "Counted twice in the total."}
                        </span>
                      </div>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-pill bg-muted text-[12px] font-medium text-foreground ml-2">
                        {merchantName}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs underline px-2 h-7"
                        onClick={() => {
                          const next = new Set(expandedMatches);
                          next.add(matchKey);
                          setExpandedMatches(next);
                        }}
                      >
                        Change
                      </Button>
                      <svg
                        width="17"
                        height="17"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        className="text-muted-foreground"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="m6 9 6 6 6-6" />
                      </svg>
                    </div>
                  </div>
                </Card>
              );
            }

            return (
              <Card key={matchKey} flush>
                <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-muted/30">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-accent text-accent-foreground">
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polygon points="12 2 2 7 12 12 22 7 12 2" />
                        <polyline points="2 17 12 22 22 17" />
                        <polyline points="2 12 12 17 22 12" />
                      </svg>
                    </span>
                    <span className="text-[15px] font-bold">
                      "{itemA.name}" appears in both photos
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-pill bg-muted text-[12px] font-medium text-foreground">
                      {merchantName}
                    </span>
                  </div>
                  <span className="text-[13px] font-semibold text-muted-foreground">
                    {mIdx + 1} of {conflictsCount}
                  </span>
                </div>

                <div className="p-4 md:p-[18px]">
                  <p className="text-[15px] leading-relaxed text-foreground mb-4">
                    The receipt was shot in two overlapping frames. This line sits at the bottom of
                    the first and the top of the second &mdash; one purchase caught twice, or two
                    identical purchases?
                  </p>

                  <div className="flex flex-col md:flex-row gap-[14px] mb-[18px]">
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => {
                        void uploadStore.resolvePositionMatch(eIdx, mIdx, "same").then(() => {
                          const next = new Set(expandedMatches);
                          next.delete(matchKey);
                          setExpandedMatches(next);
                        });
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          void uploadStore.resolvePositionMatch(eIdx, mIdx, "same").then(() => {
                            const next = new Set(expandedMatches);
                            next.delete(matchKey);
                            setExpandedMatches(next);
                          });
                        }
                      }}
                      className={`cursor-pointer flex flex-col gap-2.5 flex-1 p-4 rounded-[14px] border ${match.result === "same" ? "border-primary shadow-[0_0_0_1px_var(--color-primary)]" : "border-border hover:border-primary/50"}`}
                    >
                      <div className="flex items-center justify-between gap-2.5">
                        <span className="flex items-center gap-2.5 text-[14px] font-bold">
                          <span
                            className={`inline-flex items-center justify-center w-[18px] h-[18px] rounded-pill shrink-0 ${match.result === "same" ? "bg-primary text-primary-foreground" : "border-2 border-border-strong"}`}
                          >
                            {match.result === "same" && (
                              <svg
                                width="11"
                                height="11"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="3.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              >
                                <path d="M20 6 9 17l-5-5" />
                              </svg>
                            )}
                          </span>
                          One item, counted once
                        </span>
                      </div>
                      <div className="flex items-baseline justify-between border-t border-dashed border-border pt-2.5 mt-1">
                        <span className="text-[13px] font-semibold text-muted-foreground">
                          1 &times; {itemA.unit_price}
                        </span>
                        <span className="text-[17px] font-bold">
                          {itemA.total_price} {data.currency ?? "PLN"}
                        </span>
                      </div>
                    </div>

                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => {
                        void uploadStore.resolvePositionMatch(eIdx, mIdx, "different").then(() => {
                          const next = new Set(expandedMatches);
                          next.delete(matchKey);
                          setExpandedMatches(next);
                        });
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          void uploadStore
                            .resolvePositionMatch(eIdx, mIdx, "different")
                            .then(() => {
                              const next = new Set(expandedMatches);
                              next.delete(matchKey);
                              setExpandedMatches(next);
                            });
                        }
                      }}
                      className={`cursor-pointer flex flex-col gap-2.5 flex-1 p-4 rounded-[14px] border ${match.result === "different" ? "border-primary shadow-[0_0_0_1px_var(--color-primary)]" : "border-border hover:border-primary/50"}`}
                    >
                      <span className="flex items-center gap-2.5 text-[14px] font-bold">
                        <span
                          className={`inline-flex items-center justify-center w-[18px] h-[18px] rounded-pill shrink-0 ${match.result === "different" ? "bg-primary text-primary-foreground" : "border-2 border-border-strong"}`}
                        >
                          {match.result === "different" && (
                            <svg
                              width="11"
                              height="11"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="3.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <path d="M20 6 9 17l-5-5" />
                            </svg>
                          )}
                        </span>
                        Two items, counted twice
                      </span>
                      <div className="flex items-baseline justify-between border-t border-dashed border-border pt-2.5 mt-1">
                        <span className="text-[13px] font-semibold text-muted-foreground">
                          2 &times; {itemA.unit_price}
                        </span>
                        <span className="text-[17px] font-bold">
                          {(parseFloat(itemA.total_price) * 2).toFixed(2)} {data.currency ?? "PLN"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <Card className="p-1 pb-3 px-3.5">
                    <div className="grid grid-cols-[108px_1fr_1fr_24px] items-center gap-3 py-2 text-[13px]">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground"></span>
                      <span className="flex items-center gap-2 text-[12px] font-semibold text-primary">
                        <span className="w-2 h-2 rounded-full bg-primary"></span>Photo 1, bottom
                      </span>
                      <span className="flex items-center gap-2 text-[12px] font-semibold text-accent">
                        <span className="w-2 h-2 rounded-full bg-accent"></span>Photo 2, top
                      </span>
                      <span></span>
                    </div>

                    <div className="grid grid-cols-[108px_1fr_1fr_24px] items-center gap-3 py-2 text-[13px] border-t border-border/50">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Name
                      </span>
                      <span>{itemA.name}</span>
                      <span>{itemB.name}</span>
                      <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={
                          itemA.name === itemB.name
                            ? "var(--color-primary)"
                            : "var(--color-tone-error-text)"
                        }
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <div className="grid grid-cols-[108px_1fr_1fr_24px] items-center gap-3 py-2 text-[13px] border-t border-border/50">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Quantity
                      </span>
                      <span className="font-mono">{itemA.quantity}</span>
                      <span className="font-mono">{itemB.quantity}</span>
                      <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={
                          itemA.quantity === itemB.quantity
                            ? "var(--color-primary)"
                            : "var(--color-tone-error-text)"
                        }
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <div className="grid grid-cols-[108px_1fr_1fr_24px] items-center gap-3 py-2 text-[13px] border-t border-border/50">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Unit price
                      </span>
                      <span className="font-mono">
                        {itemA.unit_price} {data.currency ?? "PLN"}
                      </span>
                      <span className="font-mono">
                        {itemB.unit_price} {data.currency ?? "PLN"}
                      </span>
                      <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={
                          itemA.unit_price === itemB.unit_price
                            ? "var(--color-primary)"
                            : "var(--color-tone-error-text)"
                        }
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                    <div className="grid grid-cols-[108px_1fr_1fr_24px] items-center gap-3 py-2 text-[13px] border-t border-border/50">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Line total
                      </span>
                      <span className="font-mono">
                        {itemA.total_price} {data.currency ?? "PLN"}
                      </span>
                      <span className="font-mono">
                        {itemB.total_price} {data.currency ?? "PLN"}
                      </span>
                      <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={
                          itemA.total_price === itemB.total_price
                            ? "var(--color-primary)"
                            : "var(--color-tone-error-text)"
                        }
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    </div>
                  </Card>
                </div>
              </Card>
            );
          });
        })}

        <div className="flex items-center justify-between gap-4 border-t border-border pt-[18px]">
          <Button variant="ghost" onClick={handleBack}>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-2"
            >
              <path d="m15 18-6-6 6-6" />
            </svg>
            Back to what we read
          </Button>
          <div className="flex items-center gap-3.5">
            <span className="text-[13px] font-semibold text-muted-foreground">
              {conflictsCount - settledCount} still open
            </span>
            <Button variant="primary" disabled={settledCount < conflictsCount}>
              Store {extractions.length} receipts
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="ml-2"
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </Button>
          </div>
        </div>
      </Stack>
    </Container>
  );
});
