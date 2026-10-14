import type { LucideIcon } from "lucide-react";
import { ChartColumn, House, Plus, ReceiptText, Target } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

interface Tab {
  name: "home" | "receipts" | "stats" | "goals";
  path: string;
  icon: LucideIcon;
  /** Further routes this tab stands for, beyond its own. */
  alsoFor?: string[];
}

// Categories has no tab of its own: it is reached from Receipts, whose tab it lights.
const LEFT: Tab[] = [
  { name: "home", path: "/", icon: House },
  { name: "receipts", path: "/receipts", icon: ReceiptText, alsoFor: ["/categories", "/trips"] },
];
const RIGHT: Tab[] = [
  { name: "stats", path: "/statistics", icon: ChartColumn },
  { name: "goals", path: "/goals", icon: Target },
];

function isActive(tab: Tab, pathname: string): boolean {
  if (tab.path === "/") return pathname === "/";
  return [tab.path, ...(tab.alsoFor ?? [])].some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
}

/**
 * The phone's navigation, a bar along the bottom (docs/design/screens/dashboard-mobile.html).
 *
 * Five items and an upload action do not fit at 390px, so Categories moves
 * under Receipts and upload becomes the round centre button (docs/design/README.md).
 * Tablets and desktops keep the header's row of links instead.
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
        className={`flex min-h-13 flex-grow flex-col items-center justify-center gap-1 text-xs font-semibold ${
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
      className="fixed inset-x-0 bottom-0 z-10 border-t border-border bg-surface md:hidden"
    >
      <div className="flex items-center gap-1 px-3 pt-2 pb-3.5">
        {LEFT.map(tab)}
        <Link
          to="/upload"
          aria-label={t("header.uploadReceipt")}
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-pill bg-primary text-primary-foreground shadow-card"
        >
          <Plus size={24} aria-hidden="true" />
        </Link>
        {RIGHT.map(tab)}
      </div>
    </nav>
  );
}
