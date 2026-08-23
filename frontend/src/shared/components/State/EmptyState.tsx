import * as React from "react";
import type { LucideIcon } from "lucide-react";

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  message: React.ReactNode;
  action?: React.ReactNode;
  iconTone?: "neutral" | "accent" | "primary" | "warning" | "error" | "info";
}

export function EmptyState({ 
  icon: Icon, 
  title, 
  message, 
  action,
  iconTone = "neutral"
}: EmptyStateProps) {
  
  const toneClasses = {
    neutral: "bg-tone-neutral-bg text-tone-neutral-text",
    accent: "bg-tone-accent-bg text-tone-accent-text",
    primary: "bg-tone-primary-bg text-tone-primary-text",
    warning: "bg-tone-warning-bg text-tone-warning-text",
    error: "bg-tone-error-bg text-tone-error-text",
    info: "bg-tone-info-bg text-tone-info-text",
  };

  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <span className={`flex items-center justify-center shrink-0 w-11.5 h-11.5 rounded-pill ${toneClasses[iconTone]}`}>
        <Icon size={22} strokeWidth={1.8} />
      </span>
      <div className="flex flex-col gap-1.25">
        <span className="text-lg font-bold">{title}</span>
        <span className="text-base leading-[1.55] max-w-[360px]">{message}</span>
      </div>
      {action && action}
    </div>
  );
}
