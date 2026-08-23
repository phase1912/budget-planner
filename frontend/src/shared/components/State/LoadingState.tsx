import * as React from "react";
import { Loader2 } from "lucide-react";

export interface LoadingStateProps {
  title?: string;
  message?: React.ReactNode;
  layout?: "spinner" | "skeleton";
  skeletonLines?: number;
}

export function LoadingState({ 
  title = "Loading...", 
  message, 
  layout = "skeleton", 
  skeletonLines = 3 
}: LoadingStateProps) {
  
  if (layout === "spinner") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8 w-full text-center">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <div className="flex flex-col gap-1">
          <span className="text-md font-bold">{title}</span>
          {message && <span className="text-base text-muted-foreground">{message}</span>}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full gap-3">
      <div className="flex items-center gap-3">
        <span className="flex items-center justify-center shrink-0 w-8.5 h-8.5 rounded-chip bg-tone-primary-bg text-tone-primary-text">
          <Loader2 size={17} className="animate-spin" strokeWidth={2} />
        </span>
        <div className="flex flex-col gap-1 min-w-0">
          <span className="text-md font-semibold truncate">{title}</span>
          {message && <span className="text-base text-muted-foreground truncate">{message}</span>}
        </div>
      </div>
      {skeletonLines > 0 && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: skeletonLines }).map((_, i) => (
            <span
              key={i}
              className="block h-8.5 rounded-chip bg-muted animate-pulse"
              style={{ width: i === skeletonLines - 1 ? "62%" : "100%" }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
