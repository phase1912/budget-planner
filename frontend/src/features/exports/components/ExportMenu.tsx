import { useEffect, useId, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { Download } from "lucide-react";

import { Button } from "@/shared/components";
import type { ExportFormat } from "@/stores/ExportStore";
import { useTranslation } from "react-i18next";

const FORMATS: { format: ExportFormat; label: string; hint: "csvHint" | "jsonHint" }[] = [
  { format: "csv", label: "CSV", hint: "csvHint" },
  { format: "json", label: "JSON", hint: "jsonHint" },
];

interface ExportMenuProps {
  /** The button's text, e.g. "Export" or "Export this list". */
  label: string;
  /** Whether an export of this kind is being written; the button says so. */
  busy: boolean;
  onExport: (format: ExportFormat) => void;
  /** An icon button beside a screen's title (design v2), its text read out instead. */
  compact?: boolean;
}

/**
 * The export button of a screen, offering CSV or JSON (BRD N6 — F7.6).
 *
 * The file holds what the screen shows; the owning store starts the export and
 * saves the file when the background job is done. Closes on a choice, Escape
 * or a click elsewhere. On a phone it takes the full width, as buttons do there.
 */
export const ExportMenu = observer(function ExportMenu({
  label,
  busy,
  onExport,
  compact = false,
}: ExportMenuProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (
        event instanceof KeyboardEvent
          ? event.key === "Escape"
          : !menu.current?.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <div ref={menu} className={`relative ${compact ? "" : "w-full md:w-auto"}`}>
      <Button
        variant="secondary"
        size="sm"
        aria-label={compact ? label : undefined}
        className={
          compact ? "h-11 w-11 justify-center p-0" : "min-h-11 w-full md:min-h-0 md:w-auto"
        }
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={id}
        disabled={busy}
        onClick={() => {
          setOpen((shown) => !shown);
        }}
      >
        <Download size={15} aria-hidden="true" />
        {!compact && (busy ? t("export.preparing") : label)}
      </Button>
      {open && (
        <ul
          id={id}
          role="menu"
          className={`absolute right-0 top-[calc(100%+6px)] z-20 m-0 flex ${compact ? "" : "w-full"} list-none flex-col gap-0.5 rounded-control border border-border bg-background p-1.5 shadow-modal ${compact ? "w-56" : "md:w-56"}`}
        >
          {FORMATS.map(({ format, label: name, hint }) => (
            <li key={format} role="none">
              <button
                type="button"
                role="menuitem"
                className="flex min-h-11 w-full cursor-pointer flex-col items-start justify-center rounded-chip px-3 py-1.5 text-left hover:bg-muted md:min-h-0"
                onClick={() => {
                  setOpen(false);
                  onExport(format);
                }}
              >
                <span className="text-md font-semibold">{name}</span>
                <span className="text-base text-muted-foreground">{t(`export.${hint}`)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
});
