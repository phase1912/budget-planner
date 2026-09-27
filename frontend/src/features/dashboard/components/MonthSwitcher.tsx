import type { ReactNode } from "react";
import { observer } from "mobx-react-lite";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { IconButton } from "@/shared/components";

interface MonthSwitcherProps {
  label: string;
  canGoForward: boolean;
  onPrevious: () => void;
  onNext: () => void;
  /** The month's status, set under its name on a phone (dashboard-mobile.html). */
  status?: ReactNode;
}

// On a phone each arrow is its own 44px bordered target at either edge; wider
// screens fold them back into the bordered group.
const ARROW =
  "h-11 w-11 md:h-auto md:w-auto md:border-transparent md:bg-transparent md:text-muted-foreground";

/**
 * "‹ September 2026 ›" — steps through calendar months, never past the current one (D2).
 *
 * A compact bordered group on a tablet or desktop; on a phone it spans the
 * width, arrows at the edges and the month centred with its status beneath.
 */
export const MonthSwitcher = observer(function MonthSwitcher({
  label,
  canGoForward,
  onPrevious,
  onNext,
  status,
}: MonthSwitcherProps) {
  return (
    <nav
      aria-label="Month"
      className="flex w-full items-center justify-between gap-2 md:inline-flex md:w-auto md:self-start md:gap-0.5 md:rounded-control md:border md:border-border md:p-0.75"
    >
      <IconButton aria-label="Previous month" onClick={onPrevious} bordered className={ARROW}>
        <ChevronLeft size={16} />
      </IconButton>
      <div className="flex flex-col items-center gap-1">
        <h2
          aria-live="polite"
          className="m-0 px-2.5 text-[16px] font-bold whitespace-nowrap md:text-[15px]"
        >
          {label}
        </h2>
        {status && <div className="md:hidden">{status}</div>}
      </div>
      <IconButton
        aria-label="Next month"
        bordered
        disabled={!canGoForward}
        onClick={onNext}
        className={ARROW}
      >
        <ChevronRight size={16} />
      </IconButton>
    </nav>
  );
});
