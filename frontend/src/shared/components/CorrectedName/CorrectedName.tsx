import { History } from "lucide-react";
import { useTranslation } from "react-i18next";

export interface CorrectedNameProps {
  /** What the receipt printed, before the user's remembered correction renamed it. */
  readName: string;
  /** Put the printed name back on this line; omitted where the receipt cannot be changed. */
  onUndo?: () => void;
  /** Also stop the shop's later receipts being corrected this way. */
  onForget?: () => void;
  busy?: boolean;
}

const ACTION =
  "inline-flex min-h-11 cursor-pointer items-center font-semibold text-muted-foreground underline underline-offset-2 hover:text-foreground disabled:cursor-default disabled:opacity-50 md:min-h-0";

/**
 * Says a line's name is the user's remembered correction of what was printed (F15.3).
 *
 * The printed name stays in view, so a correction applied by memory is never silent,
 * and it can be undone for this line or forgotten for the shop altogether.
 */
export function CorrectedName({ readName, onUndo, onForget, busy = false }: CorrectedNameProps) {
  const { t } = useTranslation();
  return (
    <span className="flex flex-wrap items-center gap-x-3 gap-y-0 text-[12px] text-muted-foreground">
      <span className="inline-flex min-w-0 items-center gap-1.5">
        <History size={12} aria-hidden="true" className="shrink-0" />
        <span className="break-all">{t("corrected.from", { name: readName })}</span>
      </span>
      {onUndo && (
        <button type="button" className={ACTION} disabled={busy} onClick={onUndo}>
          {t("corrected.undo")}
        </button>
      )}
      {onForget && (
        <button type="button" className={ACTION} disabled={busy} onClick={onForget}>
          {t("corrected.forget")}
        </button>
      )}
    </span>
  );
}
