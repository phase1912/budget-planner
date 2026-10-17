import { Plus } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { TABS, isActive } from "./tabs";

/**
 * The tablet's and desktop's navigation (F23.2): the same four places as the phone's bar,
 * down the left side — icons with small names on a tablet, a menu with names on a
 * desktop — and adding a receipt as its first, most visible item.
 */
export function SideNavigation() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("nav.main")}
      className="hidden shrink-0 flex-col gap-1 border-r border-border bg-surface px-2 py-4 md:flex md:w-24 lg:w-56 lg:px-3"
    >
      <Link
        to="/upload"
        aria-label={t("nav.add")}
        className="mb-3 flex min-h-12 flex-col items-center justify-center gap-1 rounded-control bg-primary px-2 text-xs font-bold text-primary-foreground shadow-primary lg:flex-row lg:gap-2 lg:text-md"
      >
        <Plus size={22} aria-hidden="true" />
        <span className="lg:hidden">{t("nav.addShort")}</span>
        <span className="hidden lg:inline">{t("nav.add")}</span>
      </Link>
      {TABS.map((item) => {
        const active = isActive(item, pathname);
        const Icon = item.icon;
        return (
          <Link
            key={item.name}
            to={item.path}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-control px-2 text-xs font-semibold transition-colors lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:text-md ${
              active
                ? "bg-tone-primary-bg text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Icon size={22} aria-hidden="true" />
            {t(`nav.${item.name}`)}
          </Link>
        );
      })}
    </nav>
  );
}
