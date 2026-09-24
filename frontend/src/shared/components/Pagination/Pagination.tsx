import { ChevronLeft, ChevronRight } from "lucide-react";

export interface PaginationProps {
  page: number;
  pages: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
}

const PAGE_BUTTON =
  "inline-flex items-center justify-center min-w-9 h-9 px-2.5 border rounded-chip text-md font-semibold";

/** "21–40 of 132" and previous/next buttons (docs/design/design.css, `.page-btn`). */
export function Pagination({ page, pages, size, total, onPageChange }: PaginationProps) {
  const from = total > 0 ? (page - 1) * size + 1 : 0;
  const to = Math.min(page * size, total);
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-4">
      <span className="tabular-nums text-md text-muted-foreground">
        {total > 0 ? `${String(from)}–${String(to)} of ${String(total)}` : "0 of 0"}
      </span>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          aria-label="Previous page"
          disabled={page <= 1}
          onClick={() => {
            onPageChange(page - 1);
          }}
          className={`${PAGE_BUTTON} border-border bg-background text-foreground cursor-pointer disabled:text-border-strong disabled:cursor-default`}
        >
          <ChevronLeft size={16} aria-hidden="true" />
        </button>
        <span
          aria-current="page"
          className={`${PAGE_BUTTON} border-primary bg-primary text-primary-foreground`}
        >
          {page}
        </span>
        <button
          type="button"
          aria-label="Next page"
          disabled={page >= pages}
          onClick={() => {
            onPageChange(page + 1);
          }}
          className={`${PAGE_BUTTON} border-border bg-background text-foreground cursor-pointer disabled:text-border-strong disabled:cursor-default`}
        >
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
