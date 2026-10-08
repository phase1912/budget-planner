import { Note } from "../Note";
import { Button } from "../Button/Button";
import { totalsGap } from "../../receiptTotals";

export interface TotalsGapNoteProps {
  linesSum: number;
  printedTotal: number;
  /** Add the missing discount; offered only when the lines come to more than was paid. */
  onAddDiscount?: (amount: number) => void;
  /** Open the receipt to correct a missing or misread line. */
  onFix?: () => void;
  busy?: boolean;
  /** The app already re-read the receipt and could not make it add up by itself. */
  triedToFix?: boolean;
  className?: string;
}

const money = (amount: number) => amount.toFixed(2);

/**
 * Why a receipt's lines disagree with its printed total, and the way out (BRD A9, A11).
 *
 * Lines above the total usually mean the reader missed a discount: the note names
 * the exact amount and adds it in one click, the user's call rather than ours.
 * Lines below it mean a line is missing or misread, which only the user can fix.
 * Shown only after the app has tried to reconcile the two by itself and failed
 * (`triedToFix`), which the note says, so the user knows this is not the first resort.
 * Renders nothing when the two agree within a grosz.
 */
export function TotalsGapNote({
  linesSum,
  printedTotal,
  onAddDiscount,
  onFix,
  busy = false,
  triedToFix = false,
  className,
}: TotalsGapNoteProps) {
  const totals = totalsGap(linesSum, printedTotal);
  if (totals.kind === "match") return null;

  const over = totals.kind === "over";
  return (
    <Note tone="warning" className={className}>
      <div className="flex flex-col gap-2.5">
        {triedToFix && (
          <p className="m-0 font-semibold">
            We read this receipt again and still could not make it add up, so it needs a look.
          </p>
        )}
        <p className="m-0">
          The lines come to <strong className="tabular-nums">{money(linesSum)}</strong>,{" "}
          <strong className="tabular-nums">{money(totals.gap)}</strong> {over ? "more" : "less"}{" "}
          than the <strong className="tabular-nums">{money(printedTotal)}</strong> on the receipt.{" "}
          {over
            ? "Most likely a discount was not read. Add it and the receipt counts toward your month."
            : "A line is missing or misread. Correct it and the receipt counts toward your month."}
        </p>
        <div className="flex flex-col gap-2 md:flex-row">
          {over && onAddDiscount && (
            <Button
              variant="secondary"
              size="sm"
              className="min-h-11 w-full md:min-h-0 md:w-auto"
              disabled={busy}
              onClick={() => {
                onAddDiscount(totals.gap);
              }}
            >
              Add a −{money(totals.gap)} discount
            </Button>
          )}
          {onFix && (
            <Button
              variant="ghost"
              size="sm"
              className="min-h-11 w-full md:min-h-0 md:w-auto"
              onClick={onFix}
            >
              Fix the receipt
            </Button>
          )}
        </div>
      </div>
    </Note>
  );
}
