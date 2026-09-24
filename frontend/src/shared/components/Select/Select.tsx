import * as React from "react";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  /** `warning` marks a value that still needs the user's decision. */
  tone?: "default" | "warning";
}

function borderClass(error: string | undefined, tone: SelectProps["tone"]): string {
  if (error) return "border-error text-foreground";
  if (tone === "warning") return "border-tone-warning-border text-tone-warning-text";
  return "border-border text-foreground";
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, tone = "default", id, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={id} className="text-base font-medium text-muted-foreground">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={id}
          className={`px-3 py-2.75 text-lg font-normal border rounded-control bg-background transition-shadow appearance-none
            focus:outline-none focus:border-primary focus:shadow-[var(--ring-primary)]
            disabled:bg-muted disabled:text-muted-foreground
            ${borderClass(error, tone)}
            ${className ?? ""}
          `}
          {...props}
        />
        {error && <span className="text-base text-error">{error}</span>}
      </div>
    );
  },
);
Select.displayName = "Select";
