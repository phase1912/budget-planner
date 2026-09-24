import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { Check, Pencil, Trash2, X } from "lucide-react";

import { IconButton, Input } from "@/shared/components";
import type { Category } from "@/stores/CategoriesStore";
import { CategoryDot } from "./CategoryDot";
import { formatCategoryTotals } from "./formatCategoryTotals";

interface CustomCategoryRowProps {
  category: Category;
  onRename: (name: string) => Promise<boolean>;
  onDelete: () => void;
}

/**
 * One of the user's own categories on the taxonomy screen, renamable in place (BRD C6).
 *
 * Rename and delete stay visible rather than appearing on hover, as in
 * docs/design/screens/categories.html: hover does not exist on a phone.
 */
export const CustomCategoryRow = observer(function CustomCategoryRow({
  category,
  onRename,
  onDelete,
}: CustomCategoryRowProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const editing = draft !== null;

  useEffect(() => {
    // The user just asked to rename, so taking focus is expected, not a surprise.
    if (editing) input.current?.focus();
  }, [editing]);

  const save = async () => {
    if (!draft?.trim()) return;
    if (draft.trim() === category.name || (await onRename(draft.trim()))) setDraft(null);
  };

  if (editing) {
    return (
      <form
        className="flex items-center gap-2.5"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <CategoryDot name={category.name} />
        <div className="flex-grow">
          <Input
            ref={input}
            aria-label={`New name for ${category.name}`}
            className="w-full py-1.75 text-lg"
            value={draft}
            maxLength={100}
            onChange={(e) => {
              setDraft(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Escape") setDraft(null);
            }}
          />
        </div>
        <IconButton type="submit" aria-label="Save the new name">
          <Check size={16} />
        </IconButton>
        <IconButton
          aria-label="Cancel renaming"
          onClick={() => {
            setDraft(null);
          }}
        >
          <X size={16} />
        </IconButton>
      </form>
    );
  }

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3.5 gap-y-1 md:grid-cols-[minmax(0,1fr)_auto_auto]">
      <span className="flex min-w-0 items-center gap-2.5 text-lg font-semibold text-foreground">
        <CategoryDot name={category.name} />
        <span className="truncate">{category.name}</span>
      </span>
      <span className="col-start-1 row-start-2 tabular-nums text-md text-muted-foreground whitespace-nowrap md:col-start-2 md:row-start-1">
        {formatCategoryTotals(category)}
      </span>
      <div className="col-start-2 row-span-2 row-start-1 flex items-center gap-1 md:col-start-3 md:row-span-1">
        <IconButton
          aria-label={`Rename ${category.name}`}
          onClick={() => {
            setDraft(category.name);
          }}
        >
          <Pencil size={15} />
        </IconButton>
        <IconButton tone="danger" aria-label={`Delete ${category.name}`} onClick={onDelete}>
          <Trash2 size={15} />
        </IconButton>
      </div>
    </div>
  );
});
