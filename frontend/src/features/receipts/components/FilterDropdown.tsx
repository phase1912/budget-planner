import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

import { Button } from "@/shared/components";

export interface FilterOption<T extends string> {
  value: T | undefined;
  label: string;
}

/**
 * One filter over the receipts list: a button naming the current choice and a menu of
 * the others. `undefined` is the option that filters nothing.
 */
export function FilterDropdown<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: FilterOption<T>[];
  value: T | undefined;
  onChange: (value: T | undefined) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [isOpen]);

  const current = options.find((o) => o.value === value)?.label ?? options[0]?.label;

  return (
    <div className="relative min-w-0 text-left md:inline-block" ref={containerRef}>
      <Button
        variant="secondary"
        size="sm"
        className="min-h-11 w-full justify-between md:w-auto"
        onClick={() => {
          setIsOpen(!isOpen);
        }}
        aria-label={`${label}: ${current ?? ""}`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        {/* Unset, the filter's own name is shorter than "Any status" and says the same. */}
        <span className="truncate">{value === options[0]?.value ? label : current}</span>
        <ChevronDown size={15} aria-hidden="true" className="shrink-0 text-muted-foreground" />
      </Button>

      {isOpen && (
        <div className="absolute z-10 mt-2 w-48 overflow-hidden rounded-control bg-surface shadow-modal focus:outline-none">
          <div className="py-1" role="listbox" aria-label={label}>
            {options.map((option) => (
              <button
                key={option.value ?? "any"}
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
                className={`block min-h-11 w-full px-4 py-2 text-left text-md hover:bg-muted md:min-h-0 ${
                  value === option.value
                    ? "bg-muted font-semibold text-foreground"
                    : "text-muted-foreground"
                }`}
                role="option"
                aria-selected={value === option.value}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
