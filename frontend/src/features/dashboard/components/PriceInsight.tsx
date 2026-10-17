import { observer } from "mobx-react-lite";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { formatAmount, numberFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";

const PERCENT = numberFormat({ maximumFractionDigits: 0 });

/** The price move most worth knowing, from the user's own receipts (F23.3, F23.5). */
export const PriceInsight = observer(function PriceInsight() {
  const { productsStore } = useStores();
  const { t } = useTranslation("dashboard");
  const move = productsStore.overview?.moves[0];
  if (!move) return null;
  const up = Number(move.change.difference) > 0;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <Link
      to="/products"
      className="flex items-center gap-3.5 rounded-card bg-surface p-4 text-foreground"
    >
      <span
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-control ${
          up ? "bg-tone-warning-bg text-tone-warning-text" : "bg-tone-primary-bg text-primary"
        }`}
      >
        <Icon size={22} aria-hidden="true" />
      </span>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="text-lg font-extrabold">
          {t(up ? "insight.dearer" : "insight.cheaper", {
            name: move.product.name,
            percent: PERCENT.format(Math.abs(Number(move.change.percent ?? 0))),
          })}
        </span>
        <span className="truncate text-base text-muted-foreground tabular-nums">
          {move.last_shop ? `${move.last_shop} · ` : ""}
          {formatAmount(move.change.first)} → {formatAmount(move.change.last)}
        </span>
      </span>
    </Link>
  );
});
