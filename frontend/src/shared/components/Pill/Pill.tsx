import * as React from "react";

export interface PillProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: "default" | "success" | "warning" | "error" | "info" | "accent";
  size?: "default" | "sm";
  children: React.ReactNode;
}

const TONE_CLASSES: Record<NonNullable<PillProps["tone"]>, string> = {
  default: "bg-tone-neutral-bg text-tone-neutral-text",
  success: "bg-tone-primary-bg text-tone-primary-text",
  warning: "bg-tone-warning-bg text-tone-warning-text",
  error: "bg-tone-error-bg text-tone-error-text",
  info: "bg-tone-info-bg text-tone-info-text",
  accent: "bg-tone-accent-bg text-tone-accent-text",
};

const SIZE_CLASSES: Record<NonNullable<PillProps["size"]>, string> = {
  default: "px-[11px] py-[5px]",
  sm: "px-[10px] py-[4px]",
};

export const Pill = React.forwardRef<HTMLSpanElement, PillProps>(
  ({ className = "", tone = "default", size = "default", children, ...props }, ref) => (
    <span
      ref={ref}
      className={`inline-flex items-center gap-[6px] rounded-pill text-[12px] font-semibold whitespace-nowrap ${TONE_CLASSES[tone]} ${SIZE_CLASSES[size]} ${className}`}
      {...props}
    >
      {children}
    </span>
  ),
);

Pill.displayName = "Pill";
