import type { components } from "@/api/schema";
import { Card } from "@/shared/components";

type Chart = components["schemas"]["ChartResponse"];
type BarGroup = components["schemas"]["BarGroupResponse"];

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const TICK = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

// Previous period recedes, the one asked about stands out (statistics.html). Both come
// from tokens and were run through the dataviz palette validator in light and dark.
const PREVIOUS = "bg-muted-foreground";
const CURRENT = "bg-primary";

interface CategoryChartProps {
  chart: Chart;
  /** The period on show, e.g. "1 – 27 Jul 2026". */
  current: string;
  /** The period compared against, when there is one. */
  previous: string | null;
}

/**
 * Spend per category as bars, both periods side by side (BRD E6 — F7.5), drawn
 * exactly as the server sized them: heights are shares of its round scale, so no
 * figure is re-derived here. Columns on a tablet or desktop
 * (docs/design/screens/statistics.html); on a phone, where eight pairs of columns
 * cannot fit, each category is a row of horizontal bars.
 *
 * Supplementary to the table below, which carries every value in text for the
 * keyboard and screen readers; each group is also described by its label, and its
 * figures show on hover.
 */
export function CategoryChart({ chart, current, previous }: CategoryChartProps) {
  const compared = previous !== null;
  return (
    <Card className="flex flex-col gap-4 px-4 py-4 md:px-6 md:py-5.5">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <h2 className="m-0 text-[16px] font-bold">Category by category</h2>
        {compared && (
          <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-base text-muted-foreground">
            <li className="inline-flex items-center gap-1.75">
              <span className={`h-2.5 w-2.5 rounded-[3px] ${PREVIOUS}`} aria-hidden="true" />
              {previous}
            </li>
            <li className="inline-flex items-center gap-1.75">
              <span className={`h-2.5 w-2.5 rounded-[3px] ${CURRENT}`} aria-hidden="true" />
              {current}
            </li>
          </ul>
        )}
      </div>

      <Columns chart={chart} current={current} previous={previous} />
      <Rows chart={chart} />

      {chart.hidden > 0 && (
        <p className="m-0 text-base text-muted-foreground">
          {chart.hidden === 1
            ? "One more category is in the table below."
            : `${String(chart.hidden)} more categories are in the table below.`}
        </p>
      )}
    </Card>
  );
}

function summary(group: BarGroup, current: string, previous: string | null): string {
  const name = group.name ?? "No category";
  const now = `${current}: ${AMOUNT.format(Number(group.current.value))}`;
  return group.previous && previous
    ? `${name}, ${now}; ${previous}: ${AMOUNT.format(Number(group.previous.value))}`
    : `${name}, ${now}`;
}

/** Columns rising from one baseline, with recessive gridlines at the server's ticks. */
function Columns({ chart, current, previous }: CategoryChartProps) {
  const top = Number(chart.scale_max);
  return (
    <div className="hidden md:flex md:gap-3">
      <div className="relative h-[170px] w-10 shrink-0 text-right text-sm tabular-nums text-muted-foreground">
        {chart.ticks.map((tick) => (
          <span
            key={tick}
            className="absolute right-0 translate-y-1/2"
            style={{ bottom: `${String((Number(tick) / top) * 100)}%` }}
          >
            {TICK.format(Number(tick))}
          </span>
        ))}
      </div>
      <div className="flex min-w-0 flex-grow flex-col">
        <div className="relative flex h-[170px] items-end gap-2 border-b border-border">
          {chart.ticks.slice(1).map((tick) => (
            <span
              key={tick}
              aria-hidden="true"
              className="pointer-events-none absolute inset-x-0 border-t border-muted"
              style={{ bottom: `${String((Number(tick) / top) * 100)}%` }}
            />
          ))}
          {chart.groups.map((group) => (
            <div
              key={group.category_id ?? "none"}
              role="img"
              aria-label={summary(group, current, previous)}
              className="group relative z-10 flex h-full flex-1 items-end justify-center gap-0.5 rounded-t-md hover:bg-muted/50"
            >
              {group.previous && (
                <span
                  className={`w-full max-w-6 rounded-t-[4px] ${PREVIOUS}`}
                  style={{ height: `${group.previous.height}%` }}
                />
              )}
              <span
                className={`w-full max-w-6 rounded-t-[4px] ${CURRENT}`}
                style={{ height: `${group.current.height}%` }}
              />
              <Tooltip group={group} current={current} previous={previous} />
            </div>
          ))}
        </div>
        <div className="flex gap-2 pt-2.5">
          {chart.groups.map((group) => (
            <span
              key={group.category_id ?? "none"}
              className="flex-1 truncate text-center text-base font-semibold text-muted-foreground"
            >
              {group.name ?? "No category"}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/** A group's values on hover: the figure leads, the period follows. */
function Tooltip({
  group,
  current,
  previous,
}: { group: BarGroup } & Omit<CategoryChartProps, "chart">) {
  return (
    <span
      aria-hidden="true"
      className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1 hidden -translate-x-1/2 flex-col gap-1 whitespace-nowrap rounded-control border border-border bg-background px-3 py-2 text-left shadow-modal group-hover:flex"
    >
      <span className="text-base font-semibold">{group.name ?? "No category"}</span>
      <span className="flex items-center gap-2 text-base">
        <span className={`h-0.5 w-3 ${CURRENT}`} />
        <strong className="tabular-nums">{AMOUNT.format(Number(group.current.value))}</strong>
        <span className="text-muted-foreground">{current}</span>
      </span>
      {group.previous && previous && (
        <span className="flex items-center gap-2 text-base">
          <span className={`h-0.5 w-3 ${PREVIOUS}`} />
          <strong className="tabular-nums">{AMOUNT.format(Number(group.previous.value))}</strong>
          <span className="text-muted-foreground">{previous}</span>
        </span>
      )}
    </span>
  );
}

/** On a phone: one row per category, bars growing from the left, this period's value at its tip. */
function Rows({ chart }: { chart: Chart }) {
  return (
    <ul className="m-0 flex list-none flex-col gap-3 p-0 md:hidden" aria-hidden="true">
      {chart.groups.map((group) => (
        <li key={group.category_id ?? "none"} className="flex flex-col gap-1">
          <span className="flex items-baseline justify-between gap-3 text-base">
            <span className="truncate font-semibold">{group.name ?? "No category"}</span>
            <span className="tabular-nums text-muted-foreground">
              {AMOUNT.format(Number(group.current.value))}
            </span>
          </span>
          <span className="flex flex-col gap-0.5">
            {group.previous && (
              <span
                className={`block h-2 rounded-r-[4px] ${PREVIOUS}`}
                style={{ width: `${group.previous.height}%` }}
              />
            )}
            <span
              className={`block h-2 rounded-r-[4px] ${CURRENT}`}
              style={{ width: `${group.current.height}%` }}
            />
          </span>
        </li>
      ))}
    </ul>
  );
}
