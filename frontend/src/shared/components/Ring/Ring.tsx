import type { ReactNode } from "react";

export interface RingSegment {
  value: number;
  /** A colour token, e.g. `var(--cat-dining)` or `var(--color-primary)`. */
  color: string;
}

export interface RingProps {
  segments: RingSegment[];
  /** The whole the segments are a part of; the rest of the ring shows as a track. */
  max?: number;
  /** Size and any other layout, e.g. `h-32 w-32`. */
  className?: string;
  /** How much of the radius the band takes, as a share: 0.2 is a thin ring. */
  thickness?: number;
  /** Read out instead of the picture. */
  label: string;
  children?: ReactNode;
}

/**
 * A ring chart (F23.3, F23.4): segments around a circle — a budget's share used, or a
 * month's categories — with anything in the middle. Drawn with a conic gradient of the
 * palette's tokens, so it follows the chosen palette.
 */
export function Ring({ segments, max, className, thickness = 0.2, label, children }: RingProps) {
  const sum = segments.reduce((s, x) => s + Math.max(0, x.value), 0);
  const whole = Math.max(max ?? sum, sum, Number.EPSILON);
  let at = 0;
  const stops = segments.map((x) => {
    const from = at;
    at += (Math.max(0, x.value) / whole) * 100;
    return `${x.color} ${from.toFixed(3)}% ${at.toFixed(3)}%`;
  });
  stops.push(`var(--color-border) ${at.toFixed(3)}% 100%`);
  const inset = `${String(thickness * 50)}%`;
  return (
    <div
      role="img"
      aria-label={label}
      className={`relative shrink-0 rounded-pill ${className ?? "h-32 w-32"}`}
      style={{ background: `conic-gradient(${stops.join(", ")})` }}
    >
      <div
        className="absolute flex flex-col items-center justify-center rounded-pill bg-surface text-center"
        style={{ inset }}
      >
        {children}
      </div>
    </div>
  );
}
