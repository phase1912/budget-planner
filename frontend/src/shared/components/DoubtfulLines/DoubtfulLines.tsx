import { Eye } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "../Button/Button";
import { Note } from "../Note";
import { Pill } from "../Pill";
import { SecureImage } from "../SecureImage";

export interface DoubtfulLinesNoteProps {
  /** How many lines the reader was unsure of; nothing renders at zero. */
  count: number;
  /** Whether only those lines are shown, with the photos beside them. */
  only: boolean;
  onToggle: () => void;
  /** The receipt's photos, shown while only the doubtful lines are. */
  fileIds: string[];
  photoAlt: string;
  className?: string;
}

/**
 * The lines to check on a receipt the reader was unsure of (BRD A10 — F15.2).
 *
 * Says how many there are and narrows the list to them, opening the photos at the
 * same time, so checking a receipt means comparing a few lines with the paper rather
 * than reading every line. Renders nothing when the reader was sure of every line.
 */
export function DoubtfulLinesNote({
  count,
  only,
  onToggle,
  fileIds,
  photoAlt,
  className = "",
}: DoubtfulLinesNoteProps) {
  const { t } = useTranslation();
  if (count === 0) return null;
  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <Note tone="warning">
        <span className="flex flex-col gap-2.5 md:flex-row md:items-center md:justify-between">
          <span>{t("doubtful.summary", { count })}</span>
          <Button
            variant="secondary"
            size="sm"
            aria-pressed={only}
            className="min-h-11 w-full shrink-0 md:min-h-0 md:w-auto"
            onClick={onToggle}
          >
            <Eye size={14} aria-hidden="true" />
            {only ? t("doubtful.showAll") : t("doubtful.showOnly")}
          </Button>
        </span>
      </Note>
      {only && fileIds.length > 0 && (
        <ul aria-label={t("doubtful.photos")} className="m-0 flex list-none flex-wrap gap-3 p-0">
          {fileIds.map((fileId) => (
            <li key={fileId} className="w-full md:w-[calc(50%-6px)]">
              <SecureImage
                fileId={fileId}
                alt={photoAlt}
                className="max-h-[420px] w-full rounded-md border border-border object-contain"
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The mark on one line the reader was unsure of (BRD A10 — F15.2). */
export function DoubtfulMark({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <Pill tone="warning" size="sm" title={t("doubtful.title")} className={className}>
      {t("doubtful.mark")}
    </Pill>
  );
}
