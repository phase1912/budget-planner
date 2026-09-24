import { useId, useState } from "react";
import { CalendarDays } from "lucide-react";

import { Button } from "../Button/Button";
import { Input } from "../Input/Input";
import { Modal, ModalBody, ModalFooter, ModalHeader } from "../Modal/Modal";

export interface DateRangeFilterProps {
  /** Current bounds as ISO timestamps (UTC), or undefined for "all dates". */
  start: string | undefined;
  end: string | undefined;
  onApply: (start: string | undefined, end: string | undefined) => void;
}

/**
 * A "dates" button that opens a picker for one day, one month or a range.
 *
 * Bounds are whole UTC days, since the BRD's month boundaries are UTC (CLAUDE.md).
 * The owner of the filter state decides what to do with them.
 */
export function DateRangeFilter({ start, end, onApply }: DateRangeFilterProps) {
  const id = useId();
  const [isOpen, setIsOpen] = useState(false);

  const [mode, setMode] = useState<"all" | "date" | "month" | "range">("all");
  const [singleDate, setSingleDate] = useState("");
  const [singleMonth, setSingleMonth] = useState("");
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");

  const handleOpen = () => {
    if (start && end) {
      setMode("range");
      setRangeStart(start.split("T")[0] ?? "");
      setRangeEnd(end.split("T")[0] ?? "");
    } else {
      setMode("all");
    }
    setIsOpen(true);
  };

  const applyFilter = () => {
    if (mode === "all") {
      onApply(undefined, undefined);
    } else if (mode === "date" && singleDate) {
      onApply(`${singleDate}T00:00:00Z`, `${singleDate}T23:59:59Z`);
    } else if (mode === "month" && singleMonth) {
      const year = parseInt(singleMonth.split("-")[0] ?? "2000", 10);
      const month = parseInt(singleMonth.split("-")[1] ?? "1", 10);
      const lastDay = new Date(year, month, 0).getDate();
      onApply(
        `${singleMonth}-01T00:00:00Z`,
        `${singleMonth}-${String(lastDay).padStart(2, "0")}T23:59:59Z`,
      );
    } else if (mode === "range" && rangeStart && rangeEnd) {
      onApply(`${rangeStart}T00:00:00Z`, `${rangeEnd}T23:59:59Z`);
    }
    setIsOpen(false);
  };

  const isFilterActive = Boolean(start ?? end);

  return (
    <>
      <Button variant={isFilterActive ? "primary" : "secondary"} size="sm" onClick={handleOpen}>
        <CalendarDays
          size={15}
          aria-hidden="true"
          className={isFilterActive ? "text-primary-foreground mr-1" : "text-muted-foreground mr-1"}
        />
        {isFilterActive ? "Filtered dates" : "All dates"}
      </Button>

      <Modal
        isOpen={isOpen}
        onClose={() => {
          setIsOpen(false);
        }}
        className="w-full max-w-[400px]"
      >
        <ModalHeader>
          <h2 className="text-xl font-bold">Filter by date</h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor={`${id}-mode`} className="text-sm font-medium text-muted-foreground">
              Mode
            </label>
            <select
              id={`${id}-mode`}
              className="px-3 py-2 text-base font-normal border rounded-control bg-background text-foreground border-border"
              value={mode}
              onChange={(e) => {
                setMode(e.target.value as "all" | "date" | "month" | "range");
              }}
            >
              <option value="all">All dates</option>
              <option value="date">Specific date</option>
              <option value="month">Specific month</option>
              <option value="range">Date range</option>
            </select>
          </div>

          {mode === "date" && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor={`${id}-date`} className="text-sm font-medium text-muted-foreground">
                Date
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
                Month
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
                  From
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
                  To
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
              Cancel
            </Button>
            <Button variant="primary" onClick={applyFilter}>
              Apply filter
            </Button>
          </div>
        </ModalFooter>
      </Modal>
    </>
  );
}
