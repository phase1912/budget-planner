import { useState } from "react";
import { ChevronDown, Pencil } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components";
import { dateFormat, formatAmount } from "@/i18n/format";
import type { Product } from "@/stores/ProductsStore";
import { useStores } from "@/stores/StoreContext";
import { productSize } from "../productSize";
import { CheaperMark } from "./CheaperMark";
import { RenameProductDialog } from "./RenameProductDialog";

const DAY = dateFormat({ day: "numeric", month: "short" });

/**
 * One product on the products list (F16.1): how often and where it was bought, what it
 * cost, where it recently cost less (F16.3), and — opened — every way receipts printed it, each of which can be taken out
 * into a product of its own when the matcher joined it wrongly.
 */
export const ProductRow = observer(function ProductRow({
  product,
  currency,
}: {
  product: Product;
  currency: string;
}) {
  const { productsStore } = useStores();
  const { t } = useTranslation("products");
  const size = productSize(product.size_amount, product.size_unit);
  const selected = productsStore.selected.includes(product.id);
  const splittable = product.variants.length > 1;
  const [renaming, setRenaming] = useState(false);

  return (
    <li className="flex gap-3 px-3 py-3 md:px-4.5">
      <label className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center md:h-6 md:w-6">
        <input
          type="checkbox"
          className="h-5 w-5 cursor-pointer accent-primary md:h-4 md:w-4"
          aria-label={t("select", { name: product.name })}
          checked={selected}
          onChange={() => {
            productsStore.toggle(product.id);
          }}
        />
      </label>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="min-w-0 break-words text-lg font-semibold">
            {product.name}
            {size && (
              <span className="ml-2 whitespace-nowrap text-md font-normal text-muted-foreground">
                {size}
              </span>
            )}
          </span>
          <span className="shrink-0 tabular-nums text-lg font-semibold">
            {formatAmount(product.spent)} {currency}
          </span>
        </div>
        <span className="text-base text-muted-foreground">
          {t("bought", { count: product.purchases })} · {t("shops", { count: product.shops })}
          {product.last_bought &&
            ` · ${t("last", { date: DAY.format(new Date(product.last_bought)) })}`}
        </span>
        <CheaperMark product={product} currency={currency} />
        {splittable && (
          <details className="group">
            <summary className="inline-flex min-h-11 cursor-pointer list-none items-center gap-1 text-base font-medium text-muted-foreground hover:text-foreground md:min-h-0 md:py-0.5 [&::-webkit-details-marker]:hidden">
              {t("variants", { count: product.variants.length })}
              <ChevronDown
                size={13}
                aria-hidden="true"
                className="transition-transform group-open:rotate-180"
              />
            </summary>
            <ul className="m-0 mt-1.5 flex list-none flex-col divide-y divide-border rounded-control border border-border p-0">
              {product.variants.map((variant) => (
                <li
                  key={variant.alias_id}
                  className="flex flex-col gap-1.5 px-3 py-2 md:flex-row md:items-center md:justify-between"
                >
                  <span className="flex min-w-0 flex-col">
                    <span className="break-all font-mono text-md">{variant.printed_name}</span>
                    <span className="text-base text-muted-foreground">
                      {t("bought", { count: variant.purchases })}
                    </span>
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="min-h-11 w-full md:min-h-0 md:w-auto"
                    disabled={productsStore.isSaving}
                    aria-label={t("splitLabel", { name: variant.printed_name })}
                    onClick={() => void productsStore.split(product.id, variant.alias_id)}
                  >
                    {t("split")}
                  </Button>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
      <button
        type="button"
        aria-label={t("rename.label", { name: product.name })}
        className="flex h-11 w-11 shrink-0 items-center justify-center self-start rounded-pill text-muted-foreground hover:bg-muted hover:text-foreground md:h-8 md:w-8"
        onClick={() => {
          setRenaming(true);
        }}
      >
        <Pencil size={15} aria-hidden="true" />
      </button>
      {renaming && (
        <RenameProductDialog
          productId={product.id}
          current={product.name}
          onClose={() => {
            setRenaming(false);
          }}
        />
      )}
    </li>
  );
});
