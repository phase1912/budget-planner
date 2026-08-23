import * as React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "danger-solid";
  size?: "default" | "sm" | "lg" | "compact";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "default", ...props }, ref) => {
    let variantClasses = "";
    if (variant === "primary") {
      variantClasses = "bg-primary text-primary-foreground shadow-primary hover:bg-primary-hover";
    } else if (variant === "secondary") {
      variantClasses = "bg-background text-foreground border border-border hover:bg-muted";
    } else if (variant === "ghost") {
      variantClasses = "bg-transparent text-muted-foreground hover:bg-muted";
    } else if (variant === "danger") {
      variantClasses = "bg-tone-error-bg text-tone-error-text border border-tone-error-border hover:bg-tone-error-border";
    } else {
      variantClasses = "bg-error text-background hover:opacity-90";
    }

    let sizeClasses = "";
    if (size === "default") {
      sizeClasses = "px-4 py-2.5 text-lg";
    } else if (size === "compact") {
      sizeClasses = "px-3.5 py-2.25 text-lg";
    } else if (size === "lg") {
      sizeClasses = "px-5.5 py-3.25 text-lg";
    } else {
      sizeClasses = "px-3.25 py-2 text-md";
    }

    const baseClasses = "inline-flex items-center justify-center gap-2 font-semibold rounded-control transition-colors disabled:opacity-45 disabled:pointer-events-none";

    return (
      <button
        ref={ref}
        className={`${baseClasses} ${variantClasses} ${sizeClasses} ${className ?? ""}`}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
