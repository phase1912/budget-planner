import { observer } from "mobx-react-lite";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { IconButton } from "@/shared/components";

interface MonthSwitcherProps {
  label: string;
  canGoForward: boolean;
  onPrevious: () => void;
  onNext: () => void;
}

/** "‹ September 2026 ›" — steps through calendar months, never past the current one (D2). */
export const MonthSwitcher = observer(function MonthSwitcher({
  label,
  canGoForward,
  onPrevious,
  onNext,
}: MonthSwitcherProps) {
  return (
    <nav
      aria-label="Month"
      className="inline-flex self-start items-center gap-0.5 p-0.75 border border-border rounded-control"
    >
      <IconButton aria-label="Previous month" onClick={onPrevious}>
        <ChevronLeft size={16} />
      </IconButton>
      <h2 aria-live="polite" className="m-0 px-2.5 text-[15px] font-bold whitespace-nowrap">
        {label}
      </h2>
      <IconButton aria-label="Next month" disabled={!canGoForward} onClick={onNext}>
        <ChevronRight size={16} />
      </IconButton>
    </nav>
  );
});
