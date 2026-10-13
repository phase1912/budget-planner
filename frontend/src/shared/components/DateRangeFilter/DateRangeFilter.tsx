import { useId, useState } from "react";
import { CalendarDays } from "lucide-react";

import { Button } from "../Button/Button";
import { Input } from "../Input/Input";
import { Modal, ModalBody, ModalFooter, ModalHeader } from "../Modal/Modal";
import { useTranslation } from "react-i18next";

export interface DateRangeFilterProps {
  /** Current bounds as days (YYYY-MM-DD), both included, or undefined for "all dates". */
  start: string | undefined;
  end: string | undefined;
  onApply: (start: string | undefined, end: string | undefined) => void;
  /** The button's text; defaults to "All dates" or "Filtered dates". */
  label?: string;
  /** Whether "All dates" is on offer; a screen that always needs a period turns it off. */
  allowAll?: boolean;
  /** Open the picker from outside, e.g. a "Custom" preset; uncontrolled when omitted. */
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * A "dates" button that opens a picker for one day, one month or a range.
 *
 * Bounds are whole days, both included — the one date-range rule the API applies
 * everywhere (backend app/domain/periods.py, BRD E2). The owner of the filter
 * state decides what to do with them.
 */
export function DateRangeFilter({
  start,
  end,
  onApply,
  label,
  allowAll = true,
  isOpen: openFromOutside,
  onOpenChange,
}: DateRangeFilterProps) {
  const id = useId();
  const { t } = useTranslation();
  const [openHere, setOpenHere] = useState(false);
  const isOpen = openFromOutside ?? openHere;
  const setIsOpen = (open: boolean) => {
    setOpenHere(open);
    onOpenChange?.(open);
  };

  const [mode, setMode] = useState<"all" | "date" | "month" | "range">("all");
  const [singleDate, setSingleDate] = useState("");
  const [singleMonth, setSingleMonth] = useState("");
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");

  // Seeded from the current bounds each time the picker opens, however it opens.
  const [seededFor, setSeededFor] = useState(false);
  if (isOpen && !seededFor) {
    setSeededFor(true);
    if (start && end) {
      setMode("range");
      setRangeStart(start);
      setRangeEnd(end);
    } else {
      setMode(allowAll ? "all" : "range");
    }
  } else if (!isOpen && seededFor) {
    setSeededFor(false);
  }

  const handleOpen = () => {
    setIsOpen(true);
  };

  const applyFilter = () => {
    if (mode === "all") {
      onApply(undefined, undefined);
    } else if (mode === "date" && singleDate) {
      onApply(singleDate, singleDate);
    } else if (mode === "month" && singleMonth) {
      const year = parseInt(singleMonth.split("-")[0] ?? "2000", 10);
      const month = parseInt(singleMonth.split("-")[1] ?? "1", 10);
      const lastDay = new Date(year, month, 0).getDate();
      onApply(`${singleMonth}-01`, `${singleMonth}-${String(lastDay).padStart(2, "0")}`);
    } else if (mode === "range" && rangeStart && rangeEnd) {
      onApply(rangeStart, rangeEnd);
    }
    setIsOpen(false);
  };

  const isFilterActive = Boolean(start ?? end);

  return (
    <>
      {/* With a label the button shows the chosen period rather than flagging a filter. */}
      <Button
        variant={isFilterActive && !label ? "primary" : "secondary"}
        size="sm"
        onClick={handleOpen}
      >
        <CalendarDays
          size={15}
          aria-hidden="true"
          className={
            isFilterActive && !label ? "text-primary-foreground mr-1" : "text-muted-foreground mr-1"
          }
        />
        {label ?? (isFilterActive ? t("dates.filtered") : t("dates.all"))}
      </Button>

      <Modal
        isOpen={isOpen}
        onClose={() => {
          setIsOpen(false);
        }}
        className="w-full max-w-[400px]"
      >
        <ModalHeader>
          <h2 className="text-xl font-bold">{t("dates.title")}</h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor={`${id}-mode`} className="text-sm font-medium text-muted-foreground">
              {t("dates.mode")}
            </label>
            <select
              id={`${id}-mode`}
              className="px-3 py-2 text-base font-normal border rounded-control bg-background text-foreground border-border"
              value={mode}
              onChange={(e) => {
                setMode(e.target.value as "all" | "date" | "month" | "range");
              }}
            >
              {allowAll && <option value="all">{t("dates.all")}</option>}
              <option value="date">{t("dates.specificDate")}</option>
              <option value="month">{t("dates.specificMonth")}</option>
              <option value="range">{t("dates.range")}</option>
            </select>
          </div>

          {mode === "date" && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor={`${id}-date`} className="text-sm font-medium text-muted-foreground">
                {t("dates.date")}
              </label>
              <Input
                id={`${id}-date`}
                type="date"
                value={singleDate}
                onChange={(e) => {
                  setSingleDate(e.target.value);
                }}
              />
            </div>
          )}

          {mode === "month" && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor={`${id}-month`} className="text-sm font-medium text-muted-foreground">
                {t("dates.month")}
              </label>
              <Input
                id={`${id}-month`}
                type="month"
                value={singleMonth}
                onChange={(e) => {
                  setSingleMonth(e.target.value);
                }}
              />
            </div>
          )}

          {mode === "range" && (
            <div className="flex gap-4">
              <div className="flex flex-col gap-1.5 flex-1">
                <label htmlFor={`${id}-from`} className="text-sm font-medium text-muted-foreground">
                  {t("dates.from")}
                </label>
                <Input
                  id={`${id}-from`}
                  type="date"
                  value={rangeStart}
                  onChange={(e) => {
                    setRangeStart(e.target.value);
                  }}
                />
              </div>
              <div className="flex flex-col gap-1.5 flex-1">
                <label htmlFor={`${id}-to`} className="text-sm font-medium text-muted-foreground">
                  {t("dates.to")}
                </label>
                <Input
                  id={`${id}-to`}
                  type="date"
                  value={rangeEnd}
                  onChange={(e) => {
                    setRangeEnd(e.target.value);
                  }}
                />
              </div>
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          <div />
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setIsOpen(false);
              }}
            >
              {t("cancel")}
            </Button>
            <Button variant="primary" onClick={applyFilter}>
              {t("dates.apply")}
            </Button>
          </div>
        </ModalFooter>
      </Modal>
    </>
  );
}
