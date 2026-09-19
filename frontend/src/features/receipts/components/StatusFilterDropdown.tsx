import { useState, useRef, useEffect } from "react";
import { observer } from "mobx-react-lite";
import { Button } from "@/shared/components";
import type { components } from "@/api/schema";
import { useStores } from "@/stores/StoreContext";

type ReceiptStatus = components["schemas"]["ReceiptStatus"];

export const StatusFilterDropdown = observer(() => {
  const { receiptStore } = useStores();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleOutsideClick);
    }
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [isOpen]);

  // We only show statuses that can actually exist in the receipts table.
  // UPLOADED, PARSING, and FAILED are transient job states that live in UploadJob,
  // not in the persisted Receipt table.
  const statusLabels: Partial<Record<ReceiptStatus, string>> = {
    parsed: "Parsed",
    manual_review: "Needs review",
  };

  const statuses: { value: ReceiptStatus | undefined; label: string }[] = [
    { value: undefined, label: "Any status" },
    ...(Object.entries(statusLabels) as [ReceiptStatus, string][]).map(([value, label]) => ({
      value,
      label,
    })),
  ];

  const currentStatusLabel =
    statuses.find((s) => s.value === receiptStore.statusFilter)?.label ?? "Any status";

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => {
          setIsOpen(!isOpen);
        }}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        {currentStatusLabel}
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-muted-foreground ml-1"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </Button>

      {isOpen && (
        <div className="absolute z-10 mt-2 w-48 rounded-md bg-surface shadow-lg ring-1 ring-border ring-opacity-5 focus:outline-none">
          <div className="py-1" role="listbox">
            {statuses.map((status) => (
              <button
                key={status.value ?? "any"}
                onClick={() => {
                  receiptStore.setFilters({ status: status.value });
                  setIsOpen(false);
                }}
                className={`block w-full text-left px-4 py-2 text-sm hover:bg-muted ${
                  receiptStore.statusFilter === status.value
                    ? "font-semibold text-foreground bg-muted/50"
                    : "text-muted-foreground"
                }`}
                role="option"
                aria-selected={receiptStore.statusFilter === status.value}
              >
                {status.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});
