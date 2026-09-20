import { useEffect } from "react";
import { observer } from "mobx-react-lite";

import { useStores } from "@/stores/StoreContext";
import { Card } from "@/shared/components";
import { CategoryDot } from "../components/CategoryDot";

/**
 * Read-only taxonomy page showing built-in and custom categories with
 * their item counts and totals (BRD C1, C2 — F5.1).
 *
 * F5.6 later makes this screen editable (add / rename / delete).
 * Until then the "New category" button and row actions are intentionally absent.
 */
export const CategoriesPage = observer(function CategoriesPage() {
  const { categoriesStore } = useStores();

  useEffect(() => {
    void categoriesStore.fetchCategories();
  }, [categoriesStore]);

  return (
    <div className="flex-grow flex flex-col items-center py-10 px-8">
      <div className="w-full max-w-[760px] flex flex-col gap-[22px]">
        <header className="flex items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[28px] font-bold tracking-[-0.02em] text-foreground">
              The taxonomy
            </h1>
            <p className="m-0 text-[14px] text-muted-foreground">
              Both the agent and you assign from this list.
            </p>
          </div>
        </header>

        {categoriesStore.isLoading ? (
          <div className="p-[18px] text-center text-muted-foreground">Loading…</div>
        ) : categoriesStore.error ? (
          <div className="p-[18px] text-center text-tone-error-text">{categoriesStore.error}</div>
        ) : (
          <>
            {/* ── Built-in categories ── */}
            <Card flush>
              <div className="flex items-center justify-between px-[18px] py-[13px] border-b border-border">
                <span className="text-[13px] font-bold text-foreground">Built in</span>
                <span className="text-[12px] text-muted-foreground">
                  Cannot be renamed or removed
                </span>
              </div>
              {categoriesStore.builtInCategories.map((cat, index) => (
                <div
                  key={cat.id}
                  className={`flex items-center justify-between px-[18px] py-[14px] ${
                    index === 0 ? "" : "border-t border-border"
                  }`}
                >
                  <span className="flex items-center gap-[10px] text-[14px] font-semibold text-foreground">
                    <CategoryDot name={cat.name} />
                    <span className={cat.name === "Uncategorized" ? "text-muted-foreground" : ""}>
                      {cat.name}
                    </span>
                  </span>
                  <span className="tabular-nums text-[13px] text-muted-foreground">
                    {cat.name === "Uncategorized" && cat.item_count > 0
                      ? `${String(cat.item_count)} items · awaiting your review`
                      : `${String(cat.item_count)} items · ${Number(cat.total_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`}
                  </span>
                </div>
              ))}
            </Card>

            {/* ── Custom categories ── */}
            {categoriesStore.customCategories.length > 0 && (
              <Card flush>
                <div className="flex items-center justify-between px-[18px] py-[13px] border-b border-border">
                  <span className="text-[13px] font-bold text-foreground">Yours</span>
                  <span className="text-[12px] text-muted-foreground">
                    Available to the agent from the moment you create them
                  </span>
                </div>
                {categoriesStore.customCategories.map((cat, index) => (
                  <div
                    key={cat.id}
                    className={`flex items-center justify-between px-[18px] py-[14px] ${
                      index === 0 ? "" : "border-t border-border"
                    }`}
                  >
                    <span className="flex items-center gap-[10px] text-[14px] font-semibold text-foreground">
                      <CategoryDot name={cat.name} />
                      {cat.name}
                    </span>
                    <span className="tabular-nums text-[13px] text-muted-foreground">
                      {`${String(cat.item_count)} items · ${Number(cat.total_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`}
                    </span>
                  </div>
                ))}
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
});
