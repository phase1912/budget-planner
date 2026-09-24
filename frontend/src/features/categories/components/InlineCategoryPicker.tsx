import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { ChevronDown } from "lucide-react";

import { useStores } from "@/stores/StoreContext";
import { Select } from "@/shared/components";

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
  const [isUpdating, setIsUpdating] = useState(false);
  // Ticked by default, as in docs/design/screens/categorisation.html: a correction
  // is normally meant for next time too (BRD C5).
  const [applyToFuture, setApplyToFuture] = useState(true);

  useEffect(() => {
    categoriesStore.ensureCategories();
  }, [categoriesStore]);

  const undecided = categoriesStore.isUncategorized(currentCategoryId);
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
        <Select
          aria-label={`Category for ${itemName}`}
          value={undecided ? "" : (currentCategoryId ?? "")}
          onChange={(e) => {
            void handleChange(e.target.value);
          }}
          disabled={isUpdating || categoriesStore.isLoading}
          tone={needsAttention ? "warning" : "default"}
          className="w-full cursor-pointer pr-9 py-2.25 text-md font-semibold disabled:cursor-not-allowed"
        >
          <option value="" disabled>
            Uncategorized
          </option>
          {categoriesStore.assignableBuiltIns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
          {categoriesStore.customCategories.length > 0 && (
            <optgroup label="Yours">
              {categoriesStore.customCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </optgroup>
          )}
        </Select>
        <ChevronDown
          size={15}
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
      </div>
      <label
        className="flex items-center gap-2 pl-1 text-sm text-muted-foreground"
        title={`Also apply to future ${itemName}${merchantName ? ` from ${merchantName}` : ""}`}
      >
        <input
          type="checkbox"
          checked={applyToFuture}
          onChange={(e) => {
            setApplyToFuture(e.target.checked);
          }}
          className="size-4 m-0 accent-primary"
        />
        Apply to future items
      </label>
    </div>
  );
});
