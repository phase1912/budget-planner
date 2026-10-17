import type { LucideIcon } from "lucide-react";
import { ChartPie, House, ShoppingBasket, Target } from "lucide-react";

export interface Tab {
  name: "home" | "spending" | "products" | "plan";
  path: string;
  icon: LucideIcon;
  /** Further routes this tab stands for, beyond its own. */
  alsoFor?: string[];
}

/**
 * The product's four places, named for what people do there rather than for the records
 * behind them (F23.2): receipts and categories are reached from Spending and Home, trips
 * and goals from Plan. Upload sits between them as the ＋ button.
 */
export const TABS: readonly Tab[] = [
  { name: "home", path: "/", icon: House },
  {
    name: "spending",
    path: "/spending",
    icon: ChartPie,
    alsoFor: ["/receipts", "/categories", "/statistics"],
  },
  { name: "products", path: "/products", icon: ShoppingBasket },
  { name: "plan", path: "/plan", icon: Target, alsoFor: ["/goals", "/trips", "/holidays"] },
];

export function isActive(tab: Tab, pathname: string): boolean {
  if (tab.path === "/") return pathname === "/" || pathname === "/dashboard";
  return [tab.path, ...(tab.alsoFor ?? [])].some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
}
