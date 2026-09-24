import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Plus } from "lucide-react";

import { useStores } from "@/stores/StoreContext";
import { Button, Card } from "@/shared/components";
import type { Category } from "@/stores/CategoriesStore";
import { CategoryDot } from "../components/CategoryDot";
import { CreateCategoryDialog } from "../components/CreateCategoryDialog";
import { CustomCategoryRow } from "../components/CustomCategoryRow";
import { DeleteCategoryDialog } from "../components/DeleteCategoryDialog";
import { formatCategoryTotals, formatItemCount } from "../components/formatCategoryTotals";

/**
 * The taxonomy: built-in categories with their totals, and the user's own,
 * which can be created, renamed and deleted here (BRD C1, C2, C6, C7 — F5.1, F5.6).
 *
 * Mirrors docs/design/screens/categories.html. New categories are named in a
 * dialog and are offered to the picker and the agent as soon as they are saved.
 */
export const CategoriesPage = observer(function CategoriesPage() {
  const { categoriesStore, toastStore } = useStores();
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<Category | null>(null);

  useEffect(() => {
    void categoriesStore.fetchCategories();
  }, [categoriesStore]);

  /** Run a store action and report its error, if any; true when it succeeded. */
  const report = (error: string | null): boolean => {
    if (error) toastStore.showError(error);
    return error === null;
  };

  const { customCategories } = categoriesStore;
  const showYours = customCategories.length > 0;

  return (
    <div className="flex-grow flex flex-col items-center py-10 px-4 md:px-8">
      <div className="w-full max-w-[760px] flex flex-col gap-5.5">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[28px] font-bold tracking-[-0.02em] text-foreground">
              The taxonomy
            </h1>
            <p className="m-0 text-lg text-muted-foreground">
              Both the agent and you assign from this list.
            </p>
          </div>
          <Button
            onClick={() => {
              setCreating(true);
            }}
          >
            <Plus size={16} aria-hidden="true" />
            New category
          </Button>
        </header>

        {categoriesStore.isLoading && categoriesStore.categories.length === 0 ? (
          <div className="p-4.5 text-center text-muted-foreground">Loading…</div>
        ) : categoriesStore.error ? (
          <div className="p-4.5 text-center text-tone-error-text">{categoriesStore.error}</div>
        ) : (
          <>
            <Card flush>
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5 px-4.5 py-3.25 border-b border-border">
                <h2 className="m-0 text-md font-bold text-foreground whitespace-nowrap">
                  Built in
                </h2>
                <span className="text-base text-muted-foreground">
                  Cannot be renamed or removed
                </span>
              </div>
              <ul className="m-0 p-0 list-none">
                {categoriesStore.builtInCategories.map((cat) => (
                  <li
                    key={cat.id}
                    className="flex flex-col gap-1 px-4.5 py-3.5 border-t border-border first:border-t-0 md:flex-row md:items-center md:justify-between md:gap-3"
                  >
                    <span className="flex items-center gap-2.5 text-lg font-semibold text-foreground whitespace-nowrap">
                      <CategoryDot name={cat.name} />
                      <span className={cat.name === "Uncategorized" ? "text-muted-foreground" : ""}>
                        {cat.name}
                      </span>
                    </span>
                    <span className="tabular-nums text-md text-muted-foreground whitespace-nowrap">
                      {cat.name === "Uncategorized" && cat.item_count > 0
                        ? `${formatItemCount(cat.item_count)} · awaiting your review`
                        : formatCategoryTotals(cat)}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>

            {showYours && (
              <Card flush>
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5 px-4.5 py-3.25 border-b border-border">
                  <h2 className="m-0 text-md font-bold text-foreground whitespace-nowrap">Yours</h2>
                  <span className="text-base text-muted-foreground">
                    Available to the agent from the moment you create them
                  </span>
                </div>
                <ul className="m-0 p-0 list-none">
                  {customCategories.map((cat) => (
                    <li
                      key={cat.id}
                      className="px-4.5 py-2.5 border-t border-border first:border-t-0"
                    >
                      <CustomCategoryRow
                        category={cat}
                        onRename={async (name) =>
                          report(await categoriesStore.renameCategory(cat.id, name))
                        }
                        onDelete={() => {
                          setDeleting(cat);
                        }}
                      />
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </>
        )}
      </div>

      {creating && (
        <CreateCategoryDialog
          onCreate={(name) => categoriesStore.createCategory(name)}
          onClose={() => {
            setCreating(false);
          }}
        />
      )}

      {deleting && (
        <DeleteCategoryDialog
          category={deleting}
          targets={categoriesStore.categories}
          onConfirm={async (moveToId) =>
            report(await categoriesStore.deleteCategory(deleting.id, moveToId))
          }
          onClose={() => {
            setDeleting(null);
          }}
        />
      )}
    </div>
  );
});
