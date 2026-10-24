import { Plus } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { TABS, isActive, type Tab } from "./tabs";
import { device } from "@/platform";

/**
 * The phone's navigation, a bar along the bottom (F23.2): Home and Spending, the ＋ that
 * adds a receipt or an income in the middle — the assistant is one of its ways in — then
 * Products and Plan. Tablets and desktops have the same places in the side menu instead.
 */
export function BottomNavigation() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const tab = (item: Tab) => {
    const active = isActive(item, pathname);
    const Icon = item.icon;
    return (
      <Link
        key={item.name}
        to={item.path}
        aria-current={active ? "page" : undefined}
        onClick={() => {
          if (!active) void device.feel("selected");
        }}
        className={`flex min-h-13 flex-1 flex-col items-center justify-center gap-1 text-xs font-semibold ${
          active ? "text-primary" : "text-muted-foreground"
        }`}
      >
        <Icon size={22} aria-hidden="true" />
        {t(`nav.${item.name}`)}
      </Link>
    );
  };
  return (
    <nav
      aria-label={t("nav.main")}
      className="fixed inset-x-0 bottom-0 z-10 border-t border-border bg-surface pb-safe md:hidden"
    >
      <div className="flex items-center gap-1 px-2 pt-2 pb-3.5">
        {TABS.slice(0, 2).map(tab)}
        <Link
          to="/upload"
          aria-label={t("nav.add")}
          onClick={() => {
            void device.feel("read");
          }}
          className="-mt-7 flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] bg-primary text-primary-foreground shadow-primary"
        >
          <Plus size={26} aria-hidden="true" />
        </Link>
        {TABS.slice(2).map(tab)}
      </div>
    </nav>
  );
}
