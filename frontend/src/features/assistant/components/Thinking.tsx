import { useTranslation } from "react-i18next";

/**
 * The assistant at work, visibly: three dots rising in turn beside "Thinking…", so a wait
 * of a few seconds reads as work in progress, not a frozen screen. Still for someone who
 * asked for less motion.
 */
export function Thinking() {
  const { t } = useTranslation("assistant");
  return (
    <span className="inline-flex items-center gap-3" role="status">
      <span className="inline-flex items-end gap-1" aria-hidden="true">
        {["0ms", "150ms", "300ms"].map((delay) => (
          <span
            key={delay}
            style={{ animationDelay: delay }}
            className="h-2 w-2 rounded-pill bg-primary motion-safe:animate-bounce"
          />
        ))}
      </span>
      <span className="motion-safe:animate-pulse">{t("thinking")}</span>
    </span>
  );
}
