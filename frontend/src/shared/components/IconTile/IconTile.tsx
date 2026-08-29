import * as React from "react";

export interface IconTileProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: "default" | "success" | "warning" | "error" | "info" | "accent";
  size?: "default" | "sm" | "lg" | "round";
  children: React.ReactNode;
}

export const IconTile = React.forwardRef<HTMLSpanElement, IconTileProps>(
  ({ className = "", tone = "default", size = "default", children, ...props }, ref) => {
    let toneClasses = "";
    switch (tone) {
      case "success":
        toneClasses = "bg-tone-primary-bg text-tone-primary-text";
        break;
      case "warning":
        toneClasses = "bg-tone-warning-bg text-tone-warning-text";
        break;
      case "error":
        toneClasses = "bg-tone-error-bg text-tone-error-text";
        break;
      case "info":
        toneClasses = "bg-tone-info-bg text-tone-info-text";
        break;
      case "accent":
        toneClasses = "bg-tone-accent-bg text-tone-accent-text";
        break;
      default:
        toneClasses = "bg-muted text-muted-foreground";
        break;
    }

    let sizeClasses = "";
    switch (size) {
      case "sm":
        sizeClasses = "w-[30px] h-[30px] rounded-[9px]";
        break;
      case "lg":
        sizeClasses = "w-[40px] h-[40px] rounded-control";
        break;
      case "round":
        sizeClasses = "w-[46px] h-[46px] rounded-full";
        break;
      default:
        sizeClasses = "w-[34px] h-[34px] rounded-[9px]";
        break;
    }

    const baseClasses = "inline-flex items-center justify-center shrink-0";

    return (
      <span
        ref={ref}
        className={`${baseClasses} ${toneClasses} ${sizeClasses} ${className}`}
        {...props}
      >
        {children}
      </span>
    );
  },
);
IconTile.displayName = "IconTile";
