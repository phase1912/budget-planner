import { useEffect, useState } from "react";

import { MAX_SECONDS } from "@/shared/speech";

const clock = (seconds: number) =>
  `${String(Math.floor(seconds / 60))}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

/**
 * How long the microphone has been listening, against the minute it may (F21.9.4): the
 * recording stops by itself at the end, and the bar shows it coming.
 */
export function RecordingTimer({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const tick = window.setInterval(() => {
      setNow(Date.now());
    }, 250);
    return () => {
      window.clearInterval(tick);
    };
  }, []);
  const elapsed = Math.min(Math.max((now - since) / 1000, 0), MAX_SECONDS);
  return (
    <span className="inline-flex items-center gap-2 tabular-nums">
      {clock(elapsed)} / {clock(MAX_SECONDS)}
      <span className="h-1.5 w-16 overflow-hidden rounded-pill bg-muted" aria-hidden="true">
        <span
          className="block h-full bg-error"
          style={{ width: `${String((elapsed / MAX_SECONDS) * 100)}%` }}
        />
      </span>
    </span>
  );
}
