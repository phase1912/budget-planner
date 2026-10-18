import {
  Bus,
  CircleHelp,
  HeartPulse,
  Package,
  ShoppingBasket,
  Tag,
  Ticket,
  UtensilsCrossed,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { categoryColor } from "@/shared/categoryColor";

/** Each built-in category's picture, by the English name the server stores it under (C1). */
const ICONS: Record<string, LucideIcon> = {
  Groceries: ShoppingBasket,
  Dining: UtensilsCrossed,
  Transport: Bus,
  Utilities: Zap,
  Health: HeartPulse,
  Entertainment: Ticket,
  Other: Package,
  Uncategorized: CircleHelp,
};

export interface CategoryIconProps {
  /** The category's stored name: a built-in one has its own picture, a user's own a tag. */
  name: string;
  size?: "sm" | "md" | "lg";
}

/**
 * A category's picture in a circle tinted its colour (docs/design/components.md,
 * Category mark). The colour still tells categories apart, as the dot did; the picture says
 * which at a glance. Decorative: the category's name always stands beside it.
 */
export function CategoryIcon({ name, size = "sm" }: CategoryIconProps) {
  const Icon = ICONS[name] ?? Tag;
  const color = categoryColor(name);
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center ${
        size === "sm"
          ? "h-6 w-6 rounded-full"
          : size === "md"
            ? "h-8 w-8 rounded-full"
            : "h-10 w-10 rounded-control"
      }`}
      style={{ background: `color-mix(in srgb, ${color} 18%, transparent)`, color }}
    >
      <Icon
        size={size === "sm" ? 13 : size === "md" ? 16 : 20}
        strokeWidth={size === "sm" ? 2.5 : 2}
      />
    </span>
  );
}
