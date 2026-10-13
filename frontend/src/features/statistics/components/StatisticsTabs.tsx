import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const TABS = [
  { name: "categories", path: "/statistics" },
  { name: "products", path: "/statistics/products" },
] as const;

/**
 * "Categories | Products" on Statistics (F16.1): spending by category, or by the things
 * bought. Full width on a phone, its own width on wider screens.
 */
export function StatisticsTabs() {
  const { pathname } = useLocation();
  const { t } = useTranslation("statistics");
  return (
    <nav
      aria-label={t("tabs.label")}
      className="flex w-full gap-1 rounded-control border border-border bg-muted p-1 md:w-auto md:self-start"
    >
      {TABS.map((tab) => {
        const active = pathname === tab.path;
        return (
          <Link
            key={tab.path}
            to={tab.path}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-11 flex-1 items-center justify-center rounded-chip px-4 text-lg font-semibold transition-colors md:min-h-0 md:flex-none md:py-1.75 ${
              active
                ? "bg-background text-foreground shadow-raised"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t(`tabs.${tab.name}`)}
          </Link>
        );
      })}
    </nav>
  );
}
