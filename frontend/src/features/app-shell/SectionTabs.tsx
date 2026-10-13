import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const SECTIONS = [
  { name: "receipts", path: "/receipts" },
  { name: "categories", path: "/categories" },
] as const;

/**
 * "Receipts | Categories" at the top of both screens on a phone.
 *
 * The phone's bottom bar has room for one of them (docs/design/README.md), so
 * its Receipts tab stands for both and this switch makes the other one plain to
 * see, rather than a link lost under the title. Wider screens have both in the
 * header already.
 */
export function SectionTabs() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("nav.receiptsAndCategories")}
      className="flex w-full gap-1 rounded-control border border-border bg-muted p-1 md:hidden"
    >
      {SECTIONS.map((section) => {
        const active = pathname === section.path || pathname.startsWith(`${section.path}/`);
        return (
          <Link
            key={section.path}
            to={section.path}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-11 flex-1 items-center justify-center rounded-chip text-lg font-semibold transition-colors ${
              active
                ? "bg-background text-foreground shadow-raised"
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
