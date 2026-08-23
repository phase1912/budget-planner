import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle } from "lucide-react";

export interface ErrorStateProps {
  title: string;
  message: React.ReactNode;
  icon?: LucideIcon;
  action?: React.ReactNode;
  layout?: "banner" | "panel";
}

export function ErrorState({
  title,
  message,
  icon: Icon = AlertTriangle,
  action,
  layout = "panel",
}: ErrorStateProps) {
  if (layout === "banner") {
    return (
      <div className="flex items-start w-full px-4 py-3.5 bg-tone-error-bg border border-tone-error-border rounded-control gap-3">
        <Icon size={18} className="shrink-0 mt-px text-error" strokeWidth={2} />
        <div className="flex flex-col gap-1 w-full">
          <span className="text-md font-bold text-error">{title}</span>
          <span className="text-base leading-[1.55]">{message}</span>
          {action && <div className="mt-1">{action}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full gap-3.25">
      <div className="flex items-start gap-3">
        <span className="flex items-center justify-center shrink-0 w-8.5 h-8.5 rounded-chip bg-tone-error-bg text-tone-error-text">
          <Icon size={17} strokeWidth={2} />
        </span>
        <div className="flex flex-col gap-1">
          <span className="text-md font-bold">{title}</span>
          <span className="text-base leading-[1.55]">{message}</span>
        </div>
      </div>
      {action && <div className="self-start">{action}</div>}
    </div>
  );
}
