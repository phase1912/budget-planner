import type { ReactNode } from "react";

import { sampleAmount } from "../sampleAmount";

export interface PhoneRow {
  name: string;
  sub: string;
  amount: number;
  /** A colour token, e.g. `var(--cat-groceries)`. */
  color: string;
}

/**
 * One of the app's screens drawn on the landing (F17.11, landing variant C): a phone with
 * a title, anything above the rows (a ring) and rows in the app's own look. Sample data
 * only, so it is hidden from screen readers; the text beside it says the same.
 */
export function PhoneScreen({
  title,
  rows,
  top,
  className = "",
}: {
  title: string;
  rows: PhoneRow[];
  top?: ReactNode;
  className?: string;
}) {
  return (
    <div
      aria-hidden="true"
      className={`w-full max-w-80 rounded-hero bg-surface p-3 shadow-modal ${className}`}
    >
      <div className="flex flex-col gap-2.5 rounded-hero bg-background px-4 py-5 text-left">
        <span className="text-xl font-extrabold">{title}</span>
        {top}
        {rows.map((row) => (
          <span
            key={row.name}
            className="flex min-h-12 items-center gap-2.5 rounded-control bg-surface px-3 py-2"
          >
            <span className="h-2.5 w-2.5 shrink-0 rounded-pill" style={{ background: row.color }} />
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-md font-bold">{row.name}</span>
              <span
                className={`truncate text-sm font-semibold ${row.sub.startsWith("▲") ? "text-error" : "text-muted-foreground"}`}
              >
                {row.sub}
              </span>
            </span>
            <span className="text-md font-extrabold tabular-nums">{sampleAmount(row.amount)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
