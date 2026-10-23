import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { ChevronDown } from "lucide-react";

import { useStores } from "@/stores/StoreContext";
import { Select } from "@/shared/components";
import { useTranslation } from "react-i18next";
import { categoryName } from "@/shared/categoryName";
import { CategoryIcon } from "@/shared/components";
import { NEW_CATEGORY, NewCategoryField, NewCategoryOption } from "./NewCategoryField";

interface InlineCategoryPickerProps {
  itemId: string;
  itemName: string;
  /** The receipt's merchant, which a remembered correction is scoped to (BRD C5). */
  merchantName?: string | null;
  currentCategoryId: string | null | undefined;
  /** The backend's verdict that the current category is a weak guess (BRD C3). */
  lowConfidence?: boolean;
  onCategoryChanged: () => void;
}

/**
 * Lets the owner file a line item under another category, in place (BRD C4, C5 — F5.4, F5.5).
 *
 * Used wherever a line item is shown. An item still waiting for a decision —
 * Uncategorized, or a low-confidence guess — is drawn in the warning tone so
 * it stands out in a list of settled ones. With "apply to future items" ticked
 * the choice also becomes a rule for this item from this merchant.
 */
export const InlineCategoryPicker = observer(function InlineCategoryPicker({
  itemId,
  itemName,
  merchantName,
  currentCategoryId,
  lowConfidence = false,
  onCategoryChanged,
}: InlineCategoryPickerProps) {
  const { categoriesStore, toastStore } = useStores();
  const { t } = useTranslation("categories");
  const [isUpdating, setIsUpdating] = useState(false);
  const [adding, setAdding] = useState(false);
  // Ticked by default, as in docs/design/screens/categorisation.html: a correction
  // is normally meant for next time too (BRD C5).
  const [applyToFuture, setApplyToFuture] = useState(true);

  useEffect(() => {
    categoriesStore.ensureCategories();
  }, [categoriesStore]);

  const undecided = categoriesStore.isUncategorized(currentCategoryId);
  const current = [...categoriesStore.assignableBuiltIns, ...categoriesStore.customCategories].find(
    (c) => c.id === currentCategoryId,
  );
  const needsAttention = undecided || lowConfidence;

  const handleChange = async (categoryId: string) => {
    if (!categoryId || categoryId === currentCategoryId) return;
    setIsUpdating(true);
    const error = await categoriesStore.reassignCategory(itemId, categoryId, applyToFuture);
    setIsUpdating(false);
    if (error) {
      toastStore.showError(error);
      return;
    }
    onCategoryChanged();
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="relative">
        <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2">
          <CategoryIcon name={undecided ? "Uncategorized" : (current?.name ?? "Uncategorized")} />
        </span>
        <Select
          aria-label={t("picker.label", { item: itemName })}
          value={adding ? NEW_CATEGORY : undecided ? "" : (currentCategoryId ?? "")}
          onChange={(e) => {
            if (e.target.value === NEW_CATEGORY) setAdding(true);
            else void handleChange(e.target.value);
          }}
          disabled={isUpdating || categoriesStore.isLoading}
          tone={needsAttention ? "warning" : "default"}
          className="w-full cursor-pointer pl-10 pr-9 py-2.25 text-md font-semibold disabled:cursor-not-allowed"
        >
          <option value="" disabled>
            {categoryName("Uncategorized")}
          </option>
          {categoriesStore.assignableBuiltIns.map((c) => (
            <option key={c.id} value={c.id}>
              {categoryName(c.name)}
            </option>
          ))}
          {categoriesStore.customCategories.length > 0 && (
            <optgroup label={t("picker.yours")}>
              {categoriesStore.customCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </optgroup>
          )}
          <NewCategoryOption />
        </Select>
        <ChevronDown
          size={15}
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
      </div>
      {adding && (
        <NewCategoryField
          onCreated={(id) => {
            setAdding(false);
            void handleChange(id);
          }}
          onCancel={() => {
            setAdding(false);
          }}
        />
      )}
      <label
        className="flex items-center gap-2 pl-1 text-sm text-muted-foreground"
        title={
          merchantName
            ? t("picker.applyTitleFrom", { item: itemName, merchant: merchantName })
            : t("picker.applyTitle", { item: itemName })
        }
      >
        <input
          type="checkbox"
          checked={applyToFuture}
          onChange={(e) => {
            setApplyToFuture(e.target.checked);
          }}
          className="size-4 m-0 accent-primary"
        />
        {t("picker.apply")}
      </label>
    </div>
  );
});
