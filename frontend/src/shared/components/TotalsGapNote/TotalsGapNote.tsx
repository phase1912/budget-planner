import { Note } from "../Note";
import { Button } from "../Button/Button";
import { totalsGap } from "../../receiptTotals";
import { Trans, useTranslation } from "react-i18next";
import { formatAmount } from "@/i18n/format";

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

const money = (amount: number) => formatAmount(amount);

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
  const { t } = useTranslation();
  const totals = totalsGap(linesSum, printedTotal);
  if (totals.kind === "match") return null;

  const over = totals.kind === "over";
  return (
    <Note tone="warning" className={className}>
      <div className="flex flex-col gap-2.5">
        {triedToFix && <p className="m-0 font-semibold">{t("totals.triedToFix")}</p>}
        <p className="m-0">
          <Trans
            t={t}
            i18nKey={over ? "totals.over" : "totals.under"}
            values={{ lines: money(linesSum), gap: money(totals.gap), total: money(printedTotal) }}
            components={{ b: <strong className="tabular-nums" /> }}
          />
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
              {t("totals.addDiscount", { gap: money(totals.gap) })}
            </Button>
          )}
          {onFix && (
            <Button
              variant="ghost"
              size="sm"
              className="min-h-11 w-full md:min-h-0 md:w-auto"
              onClick={onFix}
            >
              {t("totals.fix")}
            </Button>
          )}
        </div>
      </div>
    </Note>
  );
}
