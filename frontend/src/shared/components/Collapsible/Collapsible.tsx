import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

export interface CollapsibleProps {
  title: string;
  /** A count or an amount beside the title, so the closed section still says something. */
  aside?: ReactNode;
  /** Called the first time it opens — where a section loads what it shows. */
  onOpen?: () => void;
  defaultOpen?: boolean;
  children: ReactNode;
}

/**
 * A card that opens in place (design v2): a 56 px header with a title, a figure and a
 * chevron, and its content beneath once opened — the detail one tap away, never on
 * another page.
 */
export function Collapsible({
  title,
  aside,
  onOpen,
  defaultOpen = false,
  children,
}: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [opened, setOpened] = useState(defaultOpen);
  const id = useId();
  return (
    <section className="on-surface rounded-card bg-surface">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => {
          if (!opened) onOpen?.();
          setOpened(true);
          setOpen(!open);
        }}
        className="flex min-h-14 w-full items-center justify-between gap-3 px-4 text-left"
      >
        <span className="text-lg font-bold">{title}</span>
        <span className="flex items-center gap-2">
          {aside !== undefined && (
            <span className="text-md font-semibold text-muted-foreground tabular-nums">
              {aside}
            </span>
          )}
          <ChevronDown
            size={18}
            aria-hidden="true"
            className={`text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
          />
        </span>
      </button>
      {open && (
        <div id={id} className="flex flex-col gap-3 px-4 pb-4">
          {children}
        </div>
      )}
    </section>
  );
}
