interface MeterProps {
  /** How full the bar is, 0-100; anything past 100 draws a full bar. */
  value: number;
  tone?: "primary" | "error";
  /** Where to notch the bar, 0-100: on an over-full bar, the point the limit sat at. */
  mark?: number;
}

const clamp = (n: number) => Math.min(100, Math.max(0, n));

/**
 * A horizontal bar showing how much of something is used (docs/design/design.css
 * `.meter`). Decorative: the figure it draws must also be stated in text beside
 * it, which is what assistive technology reads.
 */
export function Meter({ value, tone = "primary", mark }: MeterProps) {
  const over = tone === "error";
  return (
    <span
      aria-hidden="true"
      className={`relative block h-2.5 overflow-hidden rounded-[5px] ${over ? "bg-background" : "bg-border"}`}
    >
      <span
        className={`block h-full rounded-[inherit] ${over ? "bg-error" : "bg-primary"}`}
        style={{ width: `${String(clamp(value))}%` }}
      />
      {mark !== undefined && (
        <span
          className="absolute top-0 h-full w-0.5 bg-background"
          style={{ left: `${String(clamp(mark))}%` }}
        />
      )}
    </span>
  );
}
