import { useEffect, useId, useState } from "react";
import { observer } from "mobx-react-lite";

import {
  Button,
  Input,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Note,
  Select,
} from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { Goal, GoalUpdate } from "@/stores/GoalsStore";
import { goalChoices, choiceOf, typeOf } from "../goalKinds";
import type { GoalChoice } from "../goalKinds";
import { WatchedLinesEditor } from "./WatchedLinesEditor";
import { useTranslation } from "react-i18next";
import { categoryName } from "@/shared/categoryName";

function sameItems(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((x, i) => x === b[i]);
}

interface GoalDialogProps {
  /** The goal being edited, or null to state a new one. */
  goal: Goal | null;
  onClose: () => void;
}

/**
 * Stating a goal, or changing one (BRD F1 — F8.1).
 *
 * One choice picks a money goal of one of the three kinds F1 names, or a
 * lifestyle goal; the fields follow it. A goal's type is fixed once made, so an
 * edit can switch between money kinds but not turn one into a lifestyle goal.
 * The server decides what is well formed, and its reason shows here when it
 * refuses. Editing a lifestyle goal also corrects the spending lines it watches
 * (F8.2). Removing a goal asks once more before it goes.
 */
export const GoalDialog = observer(function GoalDialog({ goal, onClose }: GoalDialogProps) {
  const { goalsStore, categoriesStore, authStore } = useStores();
  const { t } = useTranslation(["goals", "common"]);
  const titleId = useId();
  const currency = authStore.user?.currency ?? "PLN";
  const [choice, setChoice] = useState<GoalChoice>(goal ? choiceOf(goal) : "spending_ceiling");
  const [name, setName] = useState(goal?.name ?? "");
  const [amount, setAmount] = useState(goal?.target_amount ?? "");
  const [categoryId, setCategoryId] = useState(goal?.category_id ?? "");
  const [description, setDescription] = useState(goal?.description ?? "");
  const [watchedCategoryIds, setWatchedCategoryIds] = useState(goal?.mapped_category_ids ?? []);
  const [watchedItems, setWatchedItems] = useState(goal?.mapped_item_names ?? []);
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);

  const lifestyle = choice === "lifestyle";
  const choices = goal
    ? goalChoices().filter((c) => (goal.type === "lifestyle") === (c.value === "lifestyle"))
    : goalChoices();
  const categories = [...categoriesStore.assignableBuiltIns, ...categoriesStore.customCategories];
  // A category the model chose stays on offer even when it is not one the picker lists.
  const watchable = [
    ...categories,
    ...categoriesStore.categories.filter(
      (c) => watchedCategoryIds.includes(c.id) && !categories.some((o) => o.id === c.id),
    ),
  ];

  useEffect(() => {
    categoriesStore.ensureCategories();
  }, [categoriesStore]);

  const close = () => {
    goalsStore.clearSaveError();
    onClose();
  };

  const save = async () => {
    const { type, financial_kind } = typeOf(choice);
    const fields = {
      name,
      description: description.trim() || null,
      financial_kind,
      target_amount: lifestyle ? null : amount.trim() || null,
      category_id: choice === "category_reduction" ? categoryId || null : null,
    };
    if (!goal) {
      if (await goalsStore.create({ type, ...fields })) close();
      return;
    }
    const changes: GoalUpdate = { ...fields };
    // Sent only when corrected: once sent, the list is the user's and is never re-chosen.
    if (
      lifestyle &&
      (!sameItems(watchedCategoryIds, goal.mapped_category_ids) ||
        !sameItems(watchedItems, goal.mapped_item_names))
    ) {
      changes.mapped_category_ids = watchedCategoryIds;
      changes.mapped_item_names = watchedItems;
    }
    if (await goalsStore.update(goal.id, changes)) close();
  };

  const remove = async () => {
    if (goal && (await goalsStore.remove(goal.id))) close();
  };

  return (
    <Modal isOpen onClose={close} aria-labelledby={titleId} className="md:w-[520px]">
      <form
        className="flex min-h-0 flex-col"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <ModalHeader>
          <h2 id={titleId} className="m-0 text-[17px] font-bold">
            {goal ? t("dialog.edit") : t("dialog.new")}
          </h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-4">
          <Select
            label={t("dialog.kind")}
            value={choice}
            disabled={choices.length === 1}
            onChange={(e) => {
              setChoice(e.target.value as GoalChoice);
            }}
          >
            {choices.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </Select>
          <Input
            label={t("dialog.name")}
            value={name}
            required
            maxLength={120}
            placeholder={
              lifestyle ? t("dialog.namePlaceholderLifestyle") : t("dialog.namePlaceholder")
            }
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
          {!lifestyle && (
            <Input
              label={t("dialog.amountLabel", { label: t(`dialog.amount.${choice}`), currency })}
              value={amount}
              inputMode="decimal"
              required
              placeholder="3000.00"
              onChange={(e) => {
                setAmount(e.target.value.replace(",", "."));
              }}
            />
          )}
          {choice === "category_reduction" && (
            <Select
              label={t("dialog.category")}
              value={categoryId}
              required
              onChange={(e) => {
                setCategoryId(e.target.value);
              }}
            >
              <option value="">{t("dialog.pickCategory")}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {categoryName(c.name)}
                </option>
              ))}
            </Select>
          )}
          <label className="flex flex-col gap-1.5">
            <span className="text-base font-medium text-muted-foreground">
              {lifestyle ? t("dialog.ownWords") : t("dialog.why")}
            </span>
            <textarea
              value={description}
              maxLength={1000}
              rows={3}
              placeholder={lifestyle ? t("dialog.descriptionPlaceholder") : ""}
              className="resize-y rounded-control border border-border bg-background px-3 py-2.75 text-lg text-foreground transition-shadow focus:border-primary focus:shadow-[var(--ring-primary)] focus:outline-none"
              onChange={(e) => {
                setDescription(e.target.value);
              }}
            />
          </label>
          {lifestyle && goal && (
            <WatchedLinesEditor
              categories={watchable}
              categoryIds={watchedCategoryIds}
              items={watchedItems}
              onCategoryIdsChange={setWatchedCategoryIds}
              onItemsChange={setWatchedItems}
            />
          )}
          {goalsStore.saveError && <Note tone="error">{goalsStore.saveError}</Note>}
        </ModalBody>
        <ModalFooter>
          {goal ? (
            <Button
              type="button"
              variant="danger"
              size="sm"
              className="min-h-11 w-full md:min-h-0 md:w-auto"
              disabled={goalsStore.isSaving}
              onClick={() => {
                if (confirmingRemoval) void remove();
                else setConfirmingRemoval(true);
              }}
            >
              {confirmingRemoval ? t("dialog.confirmRemove") : t("dialog.remove")}
            </Button>
          ) : (
            <span className="hidden md:block" />
          )}
          <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
            <Button type="button" variant="ghost" onClick={close}>
              {t("common:cancel")}
            </Button>
            <Button type="submit" variant="primary" disabled={goalsStore.isSaving}>
              {goalsStore.isSaving ? t("dialog.saving") : goal ? t("dialog.save") : t("dialog.add")}
            </Button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
});
