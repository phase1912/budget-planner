import React from "react";
import type { LucideIcon } from "lucide-react";
import { AlertCircle, AlertTriangle, Info, CheckCircle } from "lucide-react";

export type NoteTone = "warning" | "error" | "info" | "accent" | "success";

export interface NoteProps {
  tone: NoteTone;
  children: React.ReactNode;
  className?: string;
}

export const Note: React.FC<NoteProps> = ({ tone, children, className }) => {
  let Icon: LucideIcon = Info;
  let containerClass = "";
  let iconClass = "";

  switch (tone) {
    case "warning":
      Icon = AlertCircle;
      containerClass = "border-tone-warning-border bg-tone-warning-bg text-tone-warning-prose";
      iconClass = "text-tone-warning-text";
      break;
    case "error":
      Icon = AlertTriangle;
      containerClass = "border-tone-error-border bg-tone-error-bg text-tone-error-prose";
      iconClass = "text-tone-error-text";
      break;
    case "info":
      Icon = Info;
      containerClass = "border-tone-info-border bg-tone-info-bg text-tone-info-prose";
      iconClass = "text-tone-info-text";
      break;
    case "accent":
      Icon = Info;
      containerClass = "border-tone-accent-border bg-tone-accent-bg text-tone-accent-prose";
      iconClass = "text-tone-accent-text";
      break;
    case "success":
      Icon = CheckCircle;
      containerClass = "border-tone-primary-border bg-tone-primary-bg text-tone-primary-text";
      iconClass = "text-tone-primary-text";
      break;
  }

  return (
    <div
      role={tone === "error" || tone === "warning" ? "alert" : "status"}
      className={`flex items-center gap-3 border rounded-control py-[13px] px-4 text-[13px] leading-relaxed ${containerClass} ${className ?? ""}`}
    >
      <Icon className={`shrink-0 ${iconClass}`} size={18} />
      <span className="grow">{children}</span>
    </div>
  );
};
