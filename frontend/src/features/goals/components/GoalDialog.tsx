import { useEffect, useId, useState } from "react";
import { observer } from "mobx-react-lite";
import { Apple, ChevronLeft, Gauge, PiggyBank, TrendingDown, type LucideIcon } from "lucide-react";

import {
  Button,
  CategoryIcon,
  Input,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Note,
  Select,
} from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";
import type { Goal, GoalUpdate } from "@/stores/GoalsStore";
import { goalChoices, choiceOf, typeOf } from "../goalKinds";
import type { GoalChoice } from "../goalKinds";
import { WatchedLinesEditor } from "./WatchedLinesEditor";
import { useTranslation } from "react-i18next";
import { categoryName } from "@/shared/categoryName";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });

/** Where a new savings goal's date starts: half a year on, the last day of that month. */
function halfAYearOn(today: string): string {
  const [year, month] = today.split("-").map(Number) as [number, number];
  const last = new Date(Date.UTC(year, month + 6, 0));
  return last.toISOString().slice(0, 10);
}

/** The four large choices a new goal starts from, in the order v2 draws them. */
const PICKS: { choice: GoalChoice; icon: LucideIcon }[] = [
  { choice: "savings_target", icon: PiggyBank },
  { choice: "category_reduction", icon: TrendingDown },
  { choice: "spending_ceiling", icon: Gauge },
  { choice: "lifestyle", icon: Apple },
];

type Step = "pick" | "details" | "check";

function sameItems(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((x, i) => x === b[i]);
}

interface GoalDialogProps {
  /** The goal being edited, or null to state a new one. */
  goal: Goal | null;
  onClose: () => void;
}

/**
 * Stating a goal, or changing one (BRD F1 — F8.1, F23.13).
 *
 * A new goal starts from four large choices — the three money kinds F1 names and a
 * lifestyle goal — then asks its name and amount, and a money goal is checked against
 * the user's recent months before it is saved: within reach, or a stretch with where
 * the money could come from. The check advises; it never blocks saving. A goal's type
 * is fixed once made, so an edit can switch between money kinds but not turn one into
 * a lifestyle goal. The server decides what is well formed, and its reason shows here
 * when it refuses. Editing a lifestyle goal also corrects the spending lines it watches
 * (F8.2). Removing a goal asks once more before it goes.
 */
export const GoalDialog = observer(function GoalDialog({ goal, onClose }: GoalDialogProps) {
  const { goalsStore, categoriesStore, authStore, bankAccountsStore, budgetStore, adviceStore } =
    useStores();
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
  // A savings goal is a sum to reach by a date, its money on a card or kept by hand (F8.11.1).
  const [targetDate, setTargetDate] = useState(
    goal ? (goal.target_date ?? "") : halfAYearOn(budgetStore.today),
  );
  const [savedAccountId, setSavedAccountId] = useState(goal?.saved_account_id ?? "");
  const [savedAmount, setSavedAmount] = useState(goal?.saved_amount ?? "");
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);
  const [step, setStep] = useState<Step>(goal ? "details" : "pick");

  const lifestyle = choice === "lifestyle";
  const saving = choice === "savings_target";
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
    if (!bankAccountsStore.loaded) void bankAccountsStore.load(budgetStore.today);
  }, [categoriesStore, bankAccountsStore, budgetStore]);

  const close = () => {
    goalsStore.clearSaveError();
    goalsStore.clearCheck();
    onClose();
  };

  const runCheck = () => {
    const { financial_kind } = typeOf(choice);
    if (!financial_kind) return;
    setStep("check");
    void goalsStore.checkPlan({
      financial_kind,
      target_amount: amount.trim(),
      category_id: choice === "category_reduction" ? categoryId || null : null,
      target_date: saving ? targetDate || null : null,
    });
  };

  const save = async () => {
    const { type, financial_kind } = typeOf(choice);
    const fields = {
      name,
      description: description.trim() || null,
      financial_kind,
      target_amount: lifestyle ? null : amount.trim() || null,
      category_id: choice === "category_reduction" ? categoryId || null : null,
      target_date: saving ? targetDate || null : null,
      saved_account_id: saving ? savedAccountId || null : null,
      saved_amount: saving && !savedAccountId ? savedAmount.trim() || null : null,
    };
    if (!goal) {
      if (await goalsStore.create({ type, ...fields })) {
        void adviceStore.loadProgress();
        close();
      }
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
    if (await goalsStore.update(goal.id, changes)) {
      void adviceStore.loadProgress();
      close();
    }
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
          if (!goal && !lifestyle && step === "details") runCheck();
          else void save();
        }}
      >
        <ModalHeader>
          <div className="flex items-center gap-2">
            {!goal && step !== "pick" && (
              <button
                type="button"
                aria-label={t("common:header.back")}
                className="-ml-2 flex h-11 w-11 items-center justify-center rounded-pill"
                onClick={() => {
                  setStep(step === "check" ? "details" : "pick");
                }}
              >
                <ChevronLeft size={20} aria-hidden="true" />
              </button>
            )}
            <h2 id={titleId} className="m-0 text-xl font-extrabold">
              {goal ? t("dialog.edit") : t("dialog.new")}
            </h2>
          </div>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-4">
          {step === "pick" && (
            <>
              <p className="m-0 text-2xl font-extrabold">{t("pick.title")}</p>
              <ul className="m-0 grid list-none grid-cols-1 gap-2.5 p-0 md:grid-cols-2">
                {PICKS.map(({ choice: option, icon: Icon }) => (
                  <li key={option}>
                    <button
                      type="button"
                      className="control-fill flex min-h-20 w-full items-center gap-3.5 rounded-card p-4 text-left md:min-h-32 md:flex-col md:items-start"
                      onClick={() => {
                        setChoice(option);
                        setStep("details");
                      }}
                    >
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
                        <Icon size={22} aria-hidden="true" />
                      </span>
                      <span className="flex flex-col gap-0.5">
                        <span className="text-lg font-extrabold">{t(`pick.${option}.title`)}</span>
                        <span className="text-md text-muted-foreground">
                          {t(`pick.${option}.sub`)}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          {step === "details" && (
            <>
              {goal && choices.length > 1 ? (
                <div
                  role="radiogroup"
                  aria-label={t("dialog.kind")}
                  className="flex flex-wrap gap-2"
                >
                  {choices.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      role="radio"
                      aria-checked={choice === c.value}
                      className={`min-h-11 rounded-pill px-3.5 text-md font-bold ${
                        choice === c.value ? "bg-primary text-primary-foreground" : "control-fill"
                      }`}
                      onClick={() => {
                        setChoice(c.value);
                      }}
                    >
                      {t(`pick.${c.value}.title`)}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="m-0 text-2xl font-extrabold">{t(`pick.${choice}.title`)}</p>
              )}
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
                <div className="relative">
                  <Input
                    label={t("dialog.amountLabel", {
                      label: t(`dialog.amount.${choice}`),
                      currency,
                    })}
                    value={amount}
                    inputMode="decimal"
                    required
                    placeholder="1000"
                    className="min-h-14 w-full pr-32 text-2xl font-extrabold tabular-nums"
                    onChange={(e) => {
                      setAmount(e.target.value.replace(",", "."));
                    }}
                  />
                  <span className="pointer-events-none absolute right-4 bottom-4 text-md font-bold text-muted-foreground">
                    {saving ? currency : t("perMonth", { currency })}
                  </span>
                </div>
              )}
              {saving && (
                <div className="flex flex-col gap-3 md:flex-row md:items-end">
                  <Input
                    type="date"
                    label={t("dialog.by")}
                    value={targetDate}
                    min={budgetStore.today}
                    onChange={(e) => {
                      setTargetDate(e.target.value);
                    }}
                  />
                  <Select
                    label={t("dialog.savedOn")}
                    value={savedAccountId}
                    onChange={(e) => {
                      setSavedAccountId(e.target.value);
                    }}
                  >
                    <option value="">{t("dialog.savedByHand")}</option>
                    {bankAccountsStore.accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </Select>
                  {!savedAccountId && (
                    <Input
                      label={t("dialog.savedAmount", { currency })}
                      value={savedAmount}
                      inputMode="decimal"
                      placeholder="0"
                      onChange={(e) => {
                        setSavedAmount(e.target.value.replace(",", "."));
                      }}
                    />
                  )}
                </div>
              )}
              {choice === "category_reduction" && (
                <div
                  role="radiogroup"
                  aria-label={t("dialog.category")}
                  className="flex flex-col gap-2"
                >
                  <span className="text-base font-medium text-muted-foreground">
                    {t("dialog.category")}
                  </span>
                  <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                    {categories.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        role="radio"
                        aria-checked={categoryId === c.id}
                        className={`control-fill flex min-h-12 items-center gap-2 rounded-control border-2 px-2.5 text-left text-md font-bold ${
                          categoryId === c.id ? "border-primary" : "border-transparent"
                        }`}
                        onClick={() => {
                          setCategoryId(c.id);
                        }}
                      >
                        <CategoryIcon name={c.name} />
                        <span className="min-w-0 truncate">{categoryName(c.name)}</span>
                      </button>
                    ))}
                  </div>
                </div>
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
                  className="resize-y rounded-control border-2 border-transparent control-fill px-3 py-2.75 text-lg text-foreground transition-shadow focus:border-primary focus:outline-none"
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
            </>
          )}

          {step === "check" && (
            <GoalCheckCard choice={choice} name={name} amount={amount} currency={currency} />
          )}
          {goalsStore.saveError && <Note tone="error">{goalsStore.saveError}</Note>}
        </ModalBody>
        {step !== "pick" && (
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
              {step === "check" ? (
                <>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setStep("details");
                    }}
                  >
                    {t("check.change")}
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={goalsStore.isSaving || goalsStore.isChecking}
                  >
                    {goalsStore.isSaving ? t("dialog.saving") : t("check.start")}
                  </Button>
                </>
              ) : (
                <>
                  <Button type="button" variant="ghost" onClick={close}>
                    {t("common:cancel")}
                  </Button>
                  <Button type="submit" variant="primary" disabled={goalsStore.isSaving}>
                    {goalsStore.isSaving
                      ? t("dialog.saving")
                      : goal
                        ? t("dialog.save")
                        : lifestyle
                          ? t("dialog.add")
                          : t("check.run")}
                  </Button>
                </>
              )}
            </div>
          </ModalFooter>
        )}
      </form>
    </Modal>
  );
});

interface GoalCheckCardProps {
  choice: GoalChoice;
  name: string;
  amount: string;
  currency: string;
}

/**
 * The check's verdict, calm whichever way it falls (F23.13, goal-check.html): within
 * reach, a stretch with the categories the gap could come from, or why it could not be
 * checked. The figures are the server's; this only words them.
 */
const GoalCheckCard = observer(function GoalCheckCard({
  choice,
  name,
  amount,
  currency,
}: GoalCheckCardProps) {
  const { goalsStore } = useStores();
  const { t } = useTranslation("goals");
  const check = goalsStore.check;
  const kind = choice === "lifestyle" ? "spending_ceiling" : choice;
  const money = (value: string | null) => WHOLE.format(Number(value ?? 0));

  if (goalsStore.isChecking || !check) {
    return (
      <p className="m-0 text-lg text-muted-foreground" aria-live="polite">
        {goalsStore.isChecking ? t("check.checking") : t("check.unknown")}
      </p>
    );
  }

  const tone =
    check.verdict === "doable"
      ? "bg-tone-primary-bg text-foreground"
      : check.verdict === "stretch"
        ? "bg-tone-warning-bg text-tone-warning-text"
        : "control-fill";
  return (
    <div className="flex flex-col gap-4" aria-live="polite">
      <div className="flex flex-col gap-1">
        <span className="text-[34px] leading-tight font-extrabold tabular-nums">
          {money(amount)} {currency}
        </span>
        <span className="text-md text-muted-foreground">
          {t("perMonth", { currency })} · {name}
        </span>
      </div>
      <section className={`flex flex-col gap-1.5 rounded-card p-4 ${tone}`}>
        <span className="text-lg font-extrabold">{t(`check.${check.verdict}`)}</span>
        <span className="text-md">
          {check.verdict === "unknown"
            ? t(`check.why.${check.unknown ?? "no_history"}`)
            : t(`check.${check.verdict === "doable" ? "doableBody" : "stretchBody"}.${kind}`, {
                usual: money(check.usual),
                gap: money(check.gap),
                currency,
              })}
        </span>
        {check.months > 0 && (
          <span className="text-sm opacity-80">{t("check.basis", { count: check.months })}</span>
        )}
      </section>
      {check.sources.length > 0 && (
        <section className="flex flex-col gap-2">
          <h3 className="m-0 text-lg font-extrabold">{t("check.sources")}</h3>
          <ul className="on-surface m-0 flex list-none flex-col divide-y divide-border overflow-hidden rounded-card p-0">
            {check.sources.map((source) => (
              <li
                key={source.category_id ?? "none"}
                className="control-fill flex items-center gap-3 px-4 py-3"
              >
                <CategoryIcon name={source.name ?? "Uncategorized"} />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="text-lg font-bold">
                    {t("check.source", { name: categoryName(source.name) })}
                  </span>
                  <span className="text-md text-muted-foreground">
                    {t("check.sourceMeta", { monthly: money(source.monthly), currency })}
                  </span>
                </span>
                <span className="shrink-0 text-lg font-extrabold text-primary tabular-nums">
                  {t("check.cut", { amount: money(source.cut), currency })}
                </span>
              </li>
            ))}
          </ul>
          <p className="m-0 text-md text-muted-foreground tabular-nums">
            {t("check.covers", {
              covered: money(String(check.sources.reduce((sum, x) => sum + Number(x.cut), 0))),
              gap: money(check.gap),
              currency,
            })}
          </p>
        </section>
      )}
      {check.swaps.length > 0 && (
        <section className="flex flex-col gap-2">
          <h3 className="m-0 text-lg font-extrabold">
            {check.family ? t("check.swapsFamily") : t("check.swaps")}
          </h3>
          <ul className="on-surface m-0 flex list-none flex-col divide-y divide-border overflow-hidden rounded-card p-0">
            {check.swaps.map((swap) => (
              <li key={swap.name} className="control-fill flex items-center gap-3 px-4 py-3">
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="text-lg font-bold">{swap.name}</span>
                  <span className="text-md text-muted-foreground">
                    {t("check.swapMeta", { shop: swap.shop, instead: swap.instead_of })}
                  </span>
                </span>
                <span className="shrink-0 text-lg font-extrabold text-primary tabular-nums">
                  {t("check.cut", { amount: money(swap.monthly_saving), currency })}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
});
