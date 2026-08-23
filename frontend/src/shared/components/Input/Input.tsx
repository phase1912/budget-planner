import * as React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={id} className="text-base font-medium text-muted-foreground">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={`px-3 py-2.75 text-lg font-normal border rounded-control bg-background text-foreground transition-shadow
            focus:outline-none focus:border-primary focus:shadow-[var(--ring-primary)]
            disabled:bg-muted disabled:text-muted-foreground
            ${error ? "border-error" : "border-border"}
            ${className ?? ""}
          `}
          {...props}
        />
        {error && <span className="text-base text-error">{error}</span>}
      </div>
    );
  },
);
Input.displayName = "Input";
