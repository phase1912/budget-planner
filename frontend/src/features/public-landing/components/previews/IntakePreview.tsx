import { Camera, Globe, Mail, PenLine, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { PreviewFrame } from "./PreviewFrame";

const ICONS: LucideIcon[] = [Camera, Mail, PenLine, Globe];
const AMOUNTS = [86.4, 129.99, 120, 85.0];

/** The ways a purchase gets in: photos, a forwarded e-receipt, typed in, a foreign one. */
export function IntakePreview() {
  const { t } = useTranslation("landing");
  const items = t("preview.intake.items", { returnObjects: true });
  return (
    <PreviewFrame>
      <span className="block pb-3 text-lg font-bold">{t("preview.intake.title")}</span>
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {items.map((item, i) => {
          const Icon = ICONS[i] ?? Camera;
          return (
            <li key={item.name} className="flex items-center justify-between gap-3">
              <span className="flex min-w-0 items-center gap-3">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-tone-primary-bg text-tone-primary-text">
                  <Icon size={16} />
                </span>
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-md font-semibold">{item.name}</span>
                  <span className="truncate text-base text-muted-foreground">{item.how}</span>
                </span>
              </span>
              <span className="shrink-0 text-md font-semibold tabular-nums">
                {formatAmount(AMOUNTS[i] ?? 0)}
              </span>
            </li>
          );
        })}
      </ul>
    </PreviewFrame>
  );
}
