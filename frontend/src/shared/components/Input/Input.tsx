import * as React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  /** Classes for the wrapper, which is what a grid or flex parent lays out. */
  containerClassName?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, containerClassName, label, error, id, ...props }, ref) => {
    // A label is tied to its field even when the caller gives no id.
    const generatedId = React.useId();
    const inputId = id ?? generatedId;
    return (
      <div className={`flex flex-col gap-1.5 ${containerClassName ?? ""}`}>
        {label && (
          <label htmlFor={inputId} className="text-base font-medium text-muted-foreground">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
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
