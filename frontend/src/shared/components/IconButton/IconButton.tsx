import * as React from "react";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Required: an icon alone says nothing to a screen reader. */
  "aria-label": string;
  tone?: "default" | "danger";
}

/** A square button holding only an icon (docs/design/design.css, `.btn-icon`). */
export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, tone = "default", type = "button", ...props }, ref) => {
    const toneClasses =
      tone === "danger"
        ? "bg-tone-error-bg text-tone-error-text hover:opacity-80"
        : "bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground";
    return (
      <button
        ref={ref}
        type={type}
        className={`inline-flex items-center justify-center p-2 border border-transparent rounded-chip cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${toneClasses} ${className ?? ""}`}
        {...props}
      />
    );
  },
);
IconButton.displayName = "IconButton";
