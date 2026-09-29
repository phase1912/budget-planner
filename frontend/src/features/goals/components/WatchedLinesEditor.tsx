import { useState } from "react";
import { Plus, X } from "lucide-react";

import { Button, Input } from "@/shared/components";

/** How many categories, and how many items, one goal can watch — as the API allows. */
const WATCHED_LINES_MAX = 20;
const ITEM_MAX_LENGTH = 120;

interface WatchedLinesEditorProps {
  /** The categories the user may pick from. */
  categories: { id: string; name: string }[];
  categoryIds: string[];
  items: string[];
  onCategoryIdsChange: (ids: string[]) => void;
  onItemsChange: (items: string[]) => void;
}

/**
 * The spending lines a lifestyle goal watches, for the user to correct (BRD F9 — F8.2).
 *
 * The model's first choice arrives filled in; each category toggles, each item can
 * be dropped, and a new item typed in. Once saved, the list is the user's and the
 * server stops choosing it for them.
 */
export function WatchedLinesEditor({
  categories,
  categoryIds,
  items,
  onCategoryIdsChange,
  onItemsChange,
}: WatchedLinesEditorProps) {
  const [draft, setDraft] = useState("");
  const newItem = draft.trim().toLowerCase();
  const canAdd = newItem.length > 0 && !items.includes(newItem) && items.length < WATCHED_LINES_MAX;

  const toggle = (id: string) => {
    onCategoryIdsChange(
      categoryIds.includes(id) ? categoryIds.filter((c) => c !== id) : [...categoryIds, id],
    );
  };
  const add = () => {
    if (!canAdd) return;
    onItemsChange([...items, newItem]);
    setDraft("");
  };

  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-3 border-0 p-0">
      <legend className="mb-1.5 p-0 text-base font-medium text-muted-foreground">
        What it watches
      </legend>

      <ul aria-label="Categories" className="m-0 flex list-none flex-wrap gap-1.75 p-0">
        {categories.map((category) => {
          const watched = categoryIds.includes(category.id);
          return (
            <li key={category.id}>
              <button
                type="button"
                aria-pressed={watched}
                disabled={!watched && categoryIds.length >= WATCHED_LINES_MAX}
                onClick={() => {
                  toggle(category.id);
                }}
                className={`inline-flex min-h-11 cursor-pointer items-center rounded-pill px-3 text-md font-semibold transition-colors disabled:opacity-45 md:min-h-0 md:py-1.25 ${
                  watched
                    ? "border border-transparent bg-tone-primary-bg text-tone-primary-text"
                    : "border border-border bg-background text-muted-foreground hover:text-foreground"
                }`}
              >
                {category.name}
              </button>
            </li>
          );
        })}
      </ul>

      {items.length > 0 && (
        <ul aria-label="Items" className="m-0 flex list-none flex-wrap gap-1.75 p-0">
          {items.map((item) => (
            <li key={item}>
              <button
                type="button"
                aria-label={`Stop watching ${item}`}
                onClick={() => {
                  onItemsChange(items.filter((i) => i !== item));
                }}
                className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-pill bg-tone-neutral-bg px-3 text-md font-semibold text-tone-neutral-text transition-colors hover:text-foreground md:min-h-0 md:py-1.25"
              >
                {item}
                <X size={13} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-end gap-2">
        <Input
          label="Add an item"
          containerClassName="min-w-0 flex-1"
          value={draft}
          maxLength={ITEM_MAX_LENGTH}
          placeholder="sugary drinks"
          onChange={(e) => {
            setDraft(e.target.value);
          }}
          onKeyDown={(e) => {
            // Enter adds the item here rather than submitting the whole goal.
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
        />
        <Button
          type="button"
          variant="secondary"
          className="min-h-11 shrink-0 md:min-h-0"
          disabled={!canAdd}
          onClick={add}
        >
          <Plus size={16} aria-hidden="true" />
          Add
        </Button>
      </div>
    </fieldset>
  );
}
