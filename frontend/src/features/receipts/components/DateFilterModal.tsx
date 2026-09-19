import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Button, Input, Modal, ModalHeader, ModalBody, ModalFooter } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

export const DateFilterModal = observer(() => {
  const { receiptStore } = useStores();
  const [isOpen, setIsOpen] = useState(false);

  const [mode, setMode] = useState<"all" | "date" | "month" | "range">("all");
  const [singleDate, setSingleDate] = useState("");
  const [singleMonth, setSingleMonth] = useState("");
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");

  const handleOpen = () => {
    if (receiptStore.startDateFilter && receiptStore.endDateFilter) {
      setMode("range");
      setRangeStart(receiptStore.startDateFilter.split("T")[0] ?? "");
      setRangeEnd(receiptStore.endDateFilter.split("T")[0] ?? "");
    } else {
      setMode("all");
    }
    setIsOpen(true);
  };

  const applyFilter = () => {
    if (mode === "all") {
      receiptStore.setFilters({ startDate: undefined, endDate: undefined });
    } else if (mode === "date" && singleDate) {
      receiptStore.setFilters({
        startDate: `${singleDate}T00:00:00Z`,
        endDate: `${singleDate}T23:59:59Z`,
      });
    } else if (mode === "month" && singleMonth) {
      const year = parseInt(singleMonth.split("-")[0] ?? "2000", 10);
      const month = parseInt(singleMonth.split("-")[1] ?? "1", 10);
      const lastDay = new Date(year, month, 0).getDate();
      receiptStore.setFilters({
        startDate: `${singleMonth}-01T00:00:00Z`,
        endDate: `${singleMonth}-${String(lastDay).padStart(2, "0")}T23:59:59Z`,
      });
    } else if (mode === "range" && rangeStart && rangeEnd) {
      receiptStore.setFilters({
        startDate: `${rangeStart}T00:00:00Z`,
        endDate: `${rangeEnd}T23:59:59Z`,
      });
    }
    setIsOpen(false);
  };

  const isFilterActive = receiptStore.startDateFilter ?? receiptStore.endDateFilter;

  return (
    <>
      <Button variant={isFilterActive ? "primary" : "secondary"} size="sm" onClick={handleOpen}>
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={isFilterActive ? "text-primary-foreground mr-1" : "text-muted-foreground mr-1"}
        >
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4" />
          <path d="M8 2v4" />
          <path d="M3 10h18" />
        </svg>
        {isFilterActive ? "Filtered dates" : "All dates"}
      </Button>

      <Modal
        isOpen={isOpen}
        onClose={() => {
          setIsOpen(false);
        }}
        className="w-[400px]"
      >
        <ModalHeader>
          <h2 className="text-xl font-bold">Filter by date</h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="mode-select" className="text-sm font-medium text-muted-foreground">
              Mode
            </label>
            <select
              id="mode-select"
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
              <label htmlFor="single-date" className="text-sm font-medium text-muted-foreground">
                Date
              </label>
              <Input
                id="single-date"
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
              <label htmlFor="single-month" className="text-sm font-medium text-muted-foreground">
                Month
              </label>
              <Input
                id="single-month"
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
                <label htmlFor="range-start" className="text-sm font-medium text-muted-foreground">
                  From
                </label>
                <Input
                  id="single-date"
                  type="date"
                  value={rangeStart}
                  onChange={(e) => {
                    setRangeStart(e.target.value);
                  }}
                />
              </div>
              <div className="flex flex-col gap-1.5 flex-1">
                <label htmlFor="range-end" className="text-sm font-medium text-muted-foreground">
                  To
                </label>
                <Input
                  id="single-date"
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
});
