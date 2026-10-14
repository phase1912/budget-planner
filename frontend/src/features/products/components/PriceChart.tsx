import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";

import { dateFormat, formatAmount } from "@/i18n/format";
import type { Exploration } from "@/stores/ExplorationStore";
import { priceUnit } from "../quantity";

type ProductPurchases = Exploration["products"][number];

const DAY = dateFormat({ day: "numeric", month: "short" });
const DAY_YEAR = dateFormat({ day: "numeric", month: "short", year: "numeric" });
const SERIES = ["var(--color-series-1)", "var(--color-series-2)", "var(--color-series-3)"];
const OTHER = "var(--color-series-other)";
const HEIGHT = 200;
const PAD = { left: 52, right: 12, top: 12, bottom: 26 };

interface Point {
  day: string;
  time: number;
  shop: string;
  price: number;
}

function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    // Without ResizeObserver (an old browser, a test page) the chart takes its first width.
    if (typeof ResizeObserver === "undefined") {
      setWidth(element.clientWidth || 320);
      return;
    }
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setWidth(entry.contentRect.width);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);
  return [ref, width];
}

function niceTicks(low: number, high: number): number[] {
  const span = high - low || Math.abs(high) || 1;
  const step = 10 ** Math.floor(Math.log10(span / 2));
  const nice = [1, 2, 5, 10].map((m) => m * step).find((s) => span / s <= 4) ?? step * 10;
  // From the step at or below the lowest price to the step at or above the highest, so no
  // point ever falls outside the plot.
  const ticks = [];
  const top = Math.ceil(high / nice) * nice;
  for (let v = Math.floor(low / nice) * nice; v <= top + 1e-9; v += nice) ticks.push(v);
  return ticks;
}

/**
 * How one product's price moved (F16.2): every purchase as a point over time, joined per
 * shop, coloured by shop — the three shops bought in most, the rest as "other" — with a
 * legend, a hover tooltip, and every purchase listed as text beside it.
 */
export function PriceChart({ product, currency }: { product: ProductPurchases; currency: string }) {
  const { t } = useTranslation("products");
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<Point | null>(null);
  const unit = priceUnit(product.product.size_unit);
  const otherName = t("explore.otherShops");

  const { points, colors } = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of product.prices) {
      const shop = p.shop ?? "—";
      counts.set(shop, (counts.get(shop) ?? 0) + 1);
    }
    const ranked = [...counts.keys()].sort(
      (a, b) => (counts.get(b) ?? 0) - (counts.get(a) ?? 0) || a.localeCompare(b),
    );
    const named = new Map(
      ranked.slice(0, SERIES.length).map((shop, i) => [shop, SERIES[i] ?? OTHER]),
    );
    const shopOf = (shop: string) => (named.has(shop) ? shop : otherName);
    const legend = new Map(named);
    if (ranked.length > SERIES.length) legend.set(otherName, OTHER);
    return {
      colors: legend,
      points: product.prices.map((p) => ({
        day: p.day,
        time: new Date(`${p.day}T00:00:00`).getTime(),
        shop: shopOf(p.shop ?? "—"),
        price: Number(p.base_price ?? p.unit_price),
      })),
    };
  }, [product.prices, otherName]);

  const plotWidth = Math.max(width - PAD.left - PAD.right, 1);
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const times = points.map((p) => p.time);
  const prices = points.map((p) => p.price);
  const [t0, t1] = [Math.min(...times), Math.max(...times)];
  const ticks = niceTicks(Math.min(...prices) * 0.95, Math.max(...prices) * 1.05);
  const [y0, y1] = [ticks[0] ?? 0, ticks[ticks.length - 1] ?? 1];
  const x = (time: number) =>
    PAD.left + (t1 === t0 ? plotWidth / 2 : ((time - t0) / (t1 - t0)) * plotWidth);
  const y = (price: number) => PAD.top + plotHeight - ((price - y0) / (y1 - y0 || 1)) * plotHeight;

  const lines = [...colors.keys()].map((shop) => ({
    shop,
    color: colors.get(shop) ?? OTHER,
    points: points.filter((p) => p.shop === shop),
  }));

  const onMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - box.left;
    const nearest = points.reduce<Point | null>(
      (best, p) => (!best || Math.abs(x(p.time) - px) < Math.abs(x(best.time) - px) ? p : best),
      null,
    );
    setHover(nearest);
  };

  return (
    <figure className="m-0 flex flex-col gap-2">
      <figcaption className="text-md font-semibold">{t("explore.priceOver", { unit })}</figcaption>
      <ul
        aria-label={t("explore.legend")}
        className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0"
      >
        {lines.map((line) => (
          <li
            key={line.shop}
            className="inline-flex items-center gap-1.5 text-base text-muted-foreground"
          >
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-full"
              style={{ background: line.color }}
            />
            {line.shop}
          </li>
        ))}
      </ul>
      <div ref={ref} className="relative w-full">
        {width > 0 && (
          <svg
            role="img"
            aria-label={t("explore.chartLabel", {
              name: product.product.name,
              count: points.length,
            })}
            width={width}
            height={HEIGHT}
            className="block touch-none"
            onPointerMove={onMove}
            onPointerLeave={() => {
              setHover(null);
            }}
          >
            {ticks.map((tick) => (
              <g key={tick}>
                <line
                  x1={PAD.left}
                  x2={width - PAD.right}
                  y1={y(tick)}
                  y2={y(tick)}
                  stroke="var(--color-border)"
                  strokeWidth={1}
                />
                <text
                  x={PAD.left - 6}
                  y={y(tick)}
                  textAnchor="end"
                  dominantBaseline="middle"
                  className="fill-muted-foreground text-[12px]"
                >
                  {formatAmount(tick)}
                </text>
              </g>
            ))}
            <text x={PAD.left} y={HEIGHT - 6} className="fill-muted-foreground text-[12px]">
              {DAY.format(t0)}
            </text>
            <text
              x={width - PAD.right}
              y={HEIGHT - 6}
              textAnchor="end"
              className="fill-muted-foreground text-[12px]"
            >
              {DAY.format(t1)}
            </text>
            {lines.map((line) => (
              <g key={line.shop}>
                {line.points.length > 1 && (
                  <polyline
                    fill="none"
                    stroke={line.color}
                    strokeWidth={2}
                    strokeLinejoin="round"
                    points={line.points
                      .map((p) => `${String(x(p.time))},${String(y(p.price))}`)
                      .join(" ")}
                  />
                )}
                {line.points.map((p, i) => (
                  <circle
                    key={`${p.day}-${String(i)}`}
                    cx={x(p.time)}
                    cy={y(p.price)}
                    r={hover === p ? 6 : 4}
                    fill={line.color}
                    stroke="var(--color-background)"
                    strokeWidth={2}
                  />
                ))}
              </g>
            ))}
            {hover && (
              <line
                x1={x(hover.time)}
                x2={x(hover.time)}
                y1={PAD.top}
                y2={PAD.top + plotHeight}
                stroke="var(--color-border-strong)"
                strokeWidth={1}
              />
            )}
          </svg>
        )}
        {hover && (
          <div
            role="status"
            className="pointer-events-none absolute top-0 z-10 rounded-control border border-border bg-background px-2.5 py-1.5 text-base shadow-raised"
            style={{
              left: Math.min(Math.max(x(hover.time) - 70, 0), Math.max(width - 140, 0)),
            }}
          >
            <span className="block font-semibold tabular-nums">
              {formatAmount(hover.price)} {currency} / {unit}
            </span>
            <span className="block text-muted-foreground">
              {hover.shop} · {DAY_YEAR.format(hover.time)}
            </span>
          </div>
        )}
      </div>
      <details className="group">
        <summary className="inline-flex min-h-11 cursor-pointer list-none items-center gap-1 text-base font-medium text-muted-foreground hover:text-foreground md:min-h-0 [&::-webkit-details-marker]:hidden">
          {t("explore.allPurchases", { count: points.length })}
          <ChevronDown
            size={13}
            aria-hidden="true"
            className="transition-transform group-open:rotate-180"
          />
        </summary>
        <ul className="m-0 mt-1.5 flex list-none flex-col gap-1 p-0">
          {product.prices.map((p, i) => (
            <li
              key={`${p.day}-${String(i)}`}
              className="flex justify-between gap-3 text-base tabular-nums"
            >
              <span className="text-muted-foreground">
                {DAY_YEAR.format(new Date(`${p.day}T00:00:00`))} · {p.shop ?? "—"}
              </span>
              <span>
                {formatAmount(p.base_price ?? p.unit_price)} {currency} / {unit}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </figure>
  );
}
