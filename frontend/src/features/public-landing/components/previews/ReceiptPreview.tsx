import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { CategoryIcon, Pill } from "@/shared/components";
import { PreviewFrame } from "./PreviewFrame";

const PRICES = [3.79, 4.49, 5.88, 2.69];

/** A receipt read line by line, each line in its category, one flagged for a look. */
export function ReceiptPreview() {
  const { t } = useTranslation("landing");
  const lines = t("preview.receipt.lines", { returnObjects: true });
  const categories = t("preview.receipt.categories", { returnObjects: true });
  const total = PRICES.reduce((sum, price) => sum + price, 0);
  return (
    <PreviewFrame>
      <div className="flex items-baseline justify-between gap-3 border-b border-border pb-3">
        <span className="text-lg font-bold">{t("preview.receipt.merchant")}</span>
        <span className="text-base text-muted-foreground">{t("preview.receipt.date")}</span>
      </div>
      <ul className="m-0 flex list-none flex-col gap-2.5 p-0 py-3">
        {lines.map((line, i) => (
          <li key={line} className="flex items-center justify-between gap-3 text-md">
            <span className="flex min-w-0 items-center gap-2">
              <CategoryIcon name={categories[i] ?? "Other"} />
              <span className="truncate">{line}</span>
            </span>
            <span className="tabular-nums font-semibold">{formatAmount(PRICES[i] ?? 0)}</span>
          </li>
        ))}
      </ul>
      <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
        <Pill size="sm" tone="warning">
          {t("preview.receipt.flag")}
        </Pill>
        <span className="text-lg font-bold tabular-nums">{formatAmount(total)} PLN</span>
      </div>
    </PreviewFrame>
  );
}
