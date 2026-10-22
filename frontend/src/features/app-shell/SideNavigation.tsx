import { observer } from "mobx-react-lite";
import { Plus, Settings, Sparkles } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useStores } from "@/stores/StoreContext";
import { TABS, isActive } from "./tabs";

/**
 * The tablet's and desktop's navigation (F23.2, design v2): the brand with the assistant
 * beside it (F21.13.5), adding a receipt as the main button, the same four places as the
 * phone's bar — icons with small names on a tablet, a menu with names on a desktop — and
 * the account at the bottom, opening Settings.
 */
export const SideNavigation = observer(function SideNavigation() {
  const { authStore } = useStores();
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const user = authStore.user;
  const initials =
    `${user?.first_name.charAt(0) ?? ""}${user?.last_name.charAt(0) ?? ""}`.toUpperCase() || "?";
  const item = (active: boolean) =>
    `flex min-h-12 flex-col items-center justify-center gap-1 rounded-control px-2 text-xs font-bold transition-colors lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:text-lg ${
      active
        ? "bg-tone-primary-bg text-primary"
        : "text-muted-foreground hover:bg-muted hover:text-foreground"
    }`;

  return (
    <nav
      aria-label={t("nav.main")}
      className="sticky top-0 hidden h-screen shrink-0 flex-col gap-1 bg-surface px-2 py-5 md:flex md:w-24 lg:w-60 lg:px-4"
    >
      <div className="mb-5 flex flex-col items-center gap-2 lg:flex-row lg:justify-between lg:px-3">
        <Link
          to="/"
          className="text-center text-lg font-extrabold text-primary lg:text-left lg:text-xl"
        >
          <span className="lg:hidden">BA</span>
          <span className="hidden lg:inline">{t("appName")}</span>
        </Link>
        <Link
          to="/assistant"
          aria-label={t("nav.assistant")}
          title={t("nav.assistant")}
          aria-current={pathname.startsWith("/assistant") ? "page" : undefined}
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-pill transition-colors ${
            pathname.startsWith("/assistant")
              ? "bg-primary text-primary-foreground"
              : "bg-tone-primary-bg text-primary hover:bg-primary hover:text-primary-foreground"
          }`}
        >
          <Sparkles size={20} aria-hidden="true" />
        </Link>
      </div>
      <Link
        to="/upload"
        aria-label={t("nav.add")}
        className="mb-4 flex min-h-13 flex-col items-center justify-center gap-1 rounded-[18px] bg-primary px-2 text-xs font-extrabold text-primary-foreground shadow-primary lg:flex-row lg:gap-2 lg:text-lg"
      >
        <Plus size={22} aria-hidden="true" />
        <span className="lg:hidden">{t("nav.addShort")}</span>
        <span className="hidden lg:inline">{t("nav.add")}</span>
      </Link>
      {TABS.map((tab) => {
        const active = isActive(tab, pathname);
        const Icon = tab.icon;
        return (
          <Link
            key={tab.name}
            to={tab.path}
            aria-current={active ? "page" : undefined}
            className={item(active)}
          >
            <Icon size={22} aria-hidden="true" />
            {t(`nav.${tab.name}`)}
          </Link>
        );
      })}
      <Link
        to="/settings"
        aria-current={pathname.startsWith("/settings") ? "page" : undefined}
        className={`mt-auto ${item(pathname.startsWith("/settings"))}`}
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-pill bg-tone-primary-bg text-sm font-extrabold text-primary">
          {initials}
        </span>
        <span className="hidden lg:inline">{t("nav.settings")}</span>
        <Settings size={18} className="lg:hidden" aria-hidden="true" />
      </Link>
    </nav>
  );
});
