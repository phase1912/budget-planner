import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { device } from "@/platform";

const SECTIONS = [
  { name: "receipts", path: "/receipts" },
  { name: "categories", path: "/categories" },
] as const;

/**
 * "Receipts | Categories" at the top of these screens, at every width (trips are in Plan,
 * F23.2). Neither has a place in the navigation of design v2 — receipts open from
 * Spending, categories from Home's "to review" — so this switch is how one reaches the
 * other.
 */
export function SectionTabs() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("nav.receiptsAndCategories")}
      className="flex w-full gap-1 rounded-control bg-surface p-1 md:w-80 md:self-start"
    >
      {SECTIONS.map((section) => {
        const active = pathname === section.path || pathname.startsWith(`${section.path}/`);
        return (
          <Link
            key={section.path}
            to={section.path}
            aria-current={active ? "page" : undefined}
            onClick={() => {
              if (!active) void device.feel("selected");
            }}
            className={`flex min-h-11 flex-1 items-center justify-center rounded-chip text-lg font-bold transition-colors ${
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t(`nav.${section.name}`)}
          </Link>
        );
      })}
    </nav>
  );
}
