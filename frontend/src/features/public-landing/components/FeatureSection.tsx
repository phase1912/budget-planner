import type { ReactNode } from "react";
import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";

export type FeatureKey = "receipts" | "spending" | "goals" | "household" | "trips";

/**
 * One thing the product does, on the landing (F17.2): a heading, a paragraph, three
 * points, and a preview of the screen. Text first on a phone; side by side from a laptop,
 * the preview alternating sides so the page reads as a walk through the product.
 */
export function FeatureSection({
  feature,
  preview,
  flip = false,
}: {
  feature: FeatureKey;
  preview: ReactNode;
  flip?: boolean;
}) {
  const { t } = useTranslation("landing");
  const points = t(`features.${feature}.points`, { returnObjects: true });
  const titleId = `feature-${feature}`;
  return (
    <section
      aria-labelledby={titleId}
      className="grid grid-cols-1 items-center gap-6 lg:grid-cols-2 lg:gap-12"
    >
      <div className={`flex flex-col gap-3 ${flip ? "lg:order-2" : ""}`}>
        <span className="text-base font-semibold uppercase tracking-[0.06em] text-primary">
          {t(`features.${feature}.eyebrow`)}
        </span>
        <h3 id={titleId} className="m-0 text-[22px] font-bold tracking-[-0.01em] md:text-[26px]">
          {t(`features.${feature}.title`)}
        </h3>
        <p className="m-0 text-lg leading-[1.6] text-muted-foreground">
          {t(`features.${feature}.text`)}
        </p>
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {points.map((point) => (
            <li key={point} className="flex items-start gap-2.5 text-md">
              <Check size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-primary" />
              {point}
            </li>
          ))}
        </ul>
      </div>
      {preview}
    </section>
  );
}
