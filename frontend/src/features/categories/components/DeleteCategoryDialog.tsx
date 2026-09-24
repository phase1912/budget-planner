import { useState } from "react";
import { observer } from "mobx-react-lite";
import { ChevronDown, Trash2 } from "lucide-react";

import { Button, IconTile, Modal, Note, Select } from "@/shared/components";
import type { Category } from "@/stores/CategoriesStore";
import { formatCategoryAmount, formatItemCount } from "./formatCategoryTotals";

interface DeleteCategoryDialogProps {
  category: Category;
  /** Every category the items could move to; the one being deleted is filtered out here. */
  targets: Category[];
  onConfirm: (moveToId: string) => Promise<boolean>;
  onClose: () => void;
}

/**
 * Asks where a deleted category's items should land (BRD C7).
 *
 * Mirrors the dialog in docs/design/screens/categories.html. "Other" is
 * preselected because it is the least surprising home for an item whose
 * category disappeared; Uncategorized is offered for sending them back to review.
 */
export const DeleteCategoryDialog = observer(function DeleteCategoryDialog({
  category,
  targets,
  onConfirm,
  onClose,
}: DeleteCategoryDialogProps) {
  const options = targets.filter((target) => target.id !== category.id);
  const [moveToId, setMoveToId] = useState(
    () => (options.find((target) => target.name === "Other") ?? options[0])?.id ?? "",
  );
  const [isDeleting, setIsDeleting] = useState(false);

  const confirm = async () => {
    setIsDeleting(true);
    const deleted = await onConfirm(moveToId);
    setIsDeleting(false);
    if (deleted) onClose();
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      aria-labelledby="delete-category-title"
      className="w-full max-w-[460px]"
    >
      <div className="flex flex-col gap-4.5 p-6">
        <div className="flex items-start gap-3.5">
          <IconTile tone="error" size="lg">
            <Trash2 size={20} />
          </IconTile>
          <div className="flex flex-col gap-1.25">
            <h2 id="delete-category-title" className="m-0 text-[17px] font-bold text-foreground">
              Delete “{category.name}”?
            </h2>
            <p className="m-0 text-lg text-muted-foreground">
              {category.item_count === 0
                ? "Nothing is filed under it yet."
                : `${formatItemCount(category.item_count)} ${category.item_count === 1 ? "is" : "are"} filed under it, worth ${formatCategoryAmount(category)} PLN. They keep their amounts — choose where they land.`}
            </p>
          </div>
        </div>

        <div className="relative">
          <Select
            id="move-to"
            label="Move those items to"
            className="w-full pr-9"
            value={moveToId}
            onChange={(e) => {
              setMoveToId(e.target.value);
            }}
          >
            {options.map((target) => (
              <option key={target.id} value={target.id}>
                {target.name}
              </option>
            ))}
          </Select>
          <ChevronDown
            size={16}
            aria-hidden="true"
            className="pointer-events-none absolute right-3 bottom-3.5 text-muted-foreground"
          />
        </div>

        <Note tone="warning" className="text-base">
          Finalised months keep the totals they were closed with. Only the category breakdown is
          rewritten.
        </Note>

        <div className="flex flex-wrap items-center justify-end gap-2.5">
          <Button variant="ghost" onClick={onClose}>
            Keep it
          </Button>
          <Button
            variant="danger-solid"
            disabled={!moveToId || isDeleting}
            onClick={() => {
              void confirm();
            }}
          >
            Delete and move
          </Button>
        </div>
      </div>
    </Modal>
  );
});
