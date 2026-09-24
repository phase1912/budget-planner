import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { ChevronDown } from "lucide-react";

import { useStores } from "@/stores/StoreContext";
import { Select } from "@/shared/components";

interface InlineCategoryPickerProps {
  itemId: string;
  itemName: string;
  currentCategoryId: string | null | undefined;
  /** The backend's verdict that the current category is a weak guess (BRD C3). */
  lowConfidence?: boolean;
  onCategoryChanged: () => void;
}

/**
 * Lets the owner file a line item under another category, in place (BRD C4 — F5.4).
 *
 * Used wherever a line item is shown. An item still waiting for a decision —
 * Uncategorized, or a low-confidence guess — is drawn in the warning tone so
 * it stands out in a list of settled ones.
 */
export const InlineCategoryPicker = observer(function InlineCategoryPicker({
  itemId,
  itemName,
  currentCategoryId,
  lowConfidence = false,
  onCategoryChanged,
}: InlineCategoryPickerProps) {
  const { categoriesStore, toastStore } = useStores();
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    categoriesStore.ensureCategories();
  }, [categoriesStore]);

  const undecided = categoriesStore.isUncategorized(currentCategoryId);
  const needsAttention = undecided || lowConfidence;

  const handleChange = async (categoryId: string) => {
    if (!categoryId || categoryId === currentCategoryId) return;
    setIsUpdating(true);
    const error = await categoriesStore.reassignCategory(itemId, categoryId);
    setIsUpdating(false);
    if (error) {
      toastStore.showError(error);
      return;
    }
    onCategoryChanged();
  };

  return (
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
  );
});
