import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { categoryName } from "@/shared/categoryName";
import { CategoryIcon, Meter } from "@/shared/components";
import { PreviewFrame } from "./PreviewFrame";

const TOTALS = [1120, 540, 230, 150];

/** The month by category against a limit, and one product cheaper in another shop. */
export function SpendingPreview() {
  const { t } = useTranslation("landing");
  const categories = t("preview.spending.categories", { returnObjects: true });
  return (
    <PreviewFrame>
      <div className="flex flex-col gap-1.5 pb-3">
        <span className="text-lg font-bold">{t("preview.spending.month")}</span>
        <Meter value={68} />
        <span className="text-base font-semibold text-primary">{t("preview.spending.limit")}</span>
      </div>
      <ul className="m-0 flex list-none flex-col gap-2.5 border-t border-border p-0 py-3">
        {categories.map((category, i) => (
          <li key={category} className="flex items-center justify-between gap-3 text-md">
            <span className="flex items-center gap-2">
              <CategoryIcon name={category} />
              {categoryName(category)}
            </span>
            <span className="tabular-nums font-semibold">{formatAmount(TOTALS[i] ?? 0)}</span>
          </li>
        ))}
      </ul>
      <div className="flex flex-col gap-0.5 rounded-control bg-muted px-3 py-2.5">
        <span className="text-md font-semibold">{t("preview.spending.product")}</span>
        <span className="text-base text-primary">{t("preview.spending.cheaper")}</span>
      </div>
    </PreviewFrame>
  );
}
