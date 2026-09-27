import * as React from "react";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
  /** What a phone shows instead of `label`, when the full one would not fit. */
  shortLabel?: string;
  /** A count shown beside the label, e.g. how many items wait in a queue. */
  badge?: number;
}

export interface SegmentedControlProps<T extends string> {
  label: string;
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  size?: "default" | "sm";
  /** Span the full width on a phone, options sharing it equally. */
  fill?: boolean;
}

/**
 * Two to four mutually exclusive modes (docs/design/components.md, `.segmented`).
 *
 * A group of toggle buttons: the current one reports `aria-pressed`. Scrolls
 * sideways on a narrow screen rather than wrapping into a ragged block.
 */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  size = "default",
  fill = false,
}: SegmentedControlProps<T>): React.ReactElement {
  const optionSize = size === "sm" ? "px-3.25 py-1.75 text-md" : "px-4 py-2.25 text-lg";
  return (
    <div
      role="group"
      aria-label={label}
      className={`${fill ? "flex w-full md:inline-flex md:w-auto" : "inline-flex"} max-w-full overflow-x-auto gap-1 p-1 border border-border rounded-control bg-muted`}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            // With a short form on screen, the full label (and count) still names it.
            aria-label={
              option.shortLabel
                ? [option.label, option.badge ? String(option.badge) : ""].join(" ").trim()
                : undefined
            }
            onClick={() => {
              onChange(option.value);
            }}
            className={`inline-flex ${fill ? "flex-1 justify-center md:flex-none" : "shrink-0"} items-center gap-2 rounded-chip font-semibold whitespace-nowrap cursor-pointer transition-colors ${optionSize} ${
              active
                ? "bg-background text-foreground shadow-raised"
                : "bg-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {option.shortLabel ? (
              <>
                <span className="md:hidden">{option.shortLabel}</span>
                <span className="hidden md:inline">{option.label}</span>
              </>
            ) : (
              option.label
            )}
            {option.badge !== undefined && option.badge > 0 && (
              <span className="inline-flex min-w-5 items-center justify-center rounded-pill bg-tone-error-bg px-1.75 text-sm font-bold tabular-nums text-tone-error-text">
                {option.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
