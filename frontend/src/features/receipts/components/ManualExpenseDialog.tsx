import { useEffect, useId, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { TripChoiceField } from "@/features/trips/components/TripChoiceField";
import { paidCurrencyOptions } from "@/features/trips/tripFormat";
import { categoryName } from "@/shared/categoryName";
import {
  Button,
  Input,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Select,
} from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { tripOnDay } from "@/stores/tripOnDay";
import type { ExpenseKind, Trip } from "@/stores/TripsStore";

const KINDS: ExpenseKind[] = ["transport", "accommodation", "meals", "other"];

/** Today on the user's clock, as a date field holds it. */
function today(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${String(now.getFullYear())}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/**
 * An expense there was no receipt for — cash for a tour, a tip, a parking meter (F20.5).
 *
 * It is stored like a receipt, so it counts everywhere one does. Opened from a trip's
 * page it goes into that trip; otherwise a date within a trip asks the same question
 * as the upload wizard — a tick for a personal trip, "the company's or mine?" for a
 * business one, which must be answered. Calls `onAdded` once it is stored.
 */
export const ManualExpenseDialog = observer(function ManualExpenseDialog({
  fromTrip,
  onClose,
  onAdded,
}: {
  fromTrip?: Trip;
  onClose: () => void;
  onAdded?: () => void;
}) {
  const { receiptStore, categoriesStore, tripsStore, authStore } = useStores();
  const { t } = useTranslation(["receipts", "trips", "common"]);
  const titleId = useId();
  const accountCurrency = authStore.user?.currency ?? "PLN";
  const [description, setDescription] = useState("");
  const [spentOn, setSpentOn] = useState(fromTrip?.start_date ?? today());
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState(accountCurrency);
  const [categoryId, setCategoryId] = useState("");
  const [kind, setKind] = useState<ExpenseKind | "">("");
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [currencies] = useState(() => paidCurrencyOptions(accountCurrency));

  useEffect(() => {
    categoriesStore.ensureCategories();
    if (tripsStore.trips.length === 0) void tripsStore.load();
  }, [categoriesStore, tripsStore]);

  const categories = [...categoriesStore.assignableBuiltIns, ...categoriesStore.customCategories];
  const fallback = categoriesStore.assignableBuiltIns.find((c) => c.name === "Other");
  const chosenCategory = (categoryId === "" ? fallback?.id : categoryId) ?? "";
  const trip = fromTrip ? null : tripOnDay(tripsStore.trips, spentOn);
  const answer = trip
    ? (answers[trip.id] ?? (trip.kind === "personal" ? true : undefined))
    : undefined;
  const amountInvalid =
    amount.trim() !== "" && !(/^\d+(\.\d{1,2})?$/.test(amount.trim()) && Number(amount) > 0);
  const ready =
    description.trim() !== "" &&
    spentOn !== "" &&
    amount.trim() !== "" &&
    !amountInvalid &&
    chosenCategory !== "" &&
    !(trip?.kind === "business" && answer === undefined);

  const save = async () => {
    if (!ready) return;
    setSaving(true);
    const placement = fromTrip
      ? { trip_chosen: true, trip_id: fromTrip.id }
      : trip && answer !== undefined && !(trip.kind === "personal" && answer)
        ? { trip_chosen: true, trip_id: answer ? trip.id : null }
        : { trip_chosen: false, trip_id: null };
    const added = await receiptStore.addManualExpense({
      description: description.trim(),
      spent_on: spentOn,
      amount: amount.trim(),
      currency: currency === accountCurrency ? null : currency,
      category_id: chosenCategory,
      kind: kind || null,
      ...placement,
    });
    setSaving(false);
    if (added) {
      onAdded?.();
      onClose();
    }
  };

  return (
    <Modal isOpen onClose={onClose} aria-labelledby={titleId} className="md:w-[520px]">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <ModalHeader>
          <div className="flex flex-col gap-1">
            <h2 id={titleId} className="m-0 text-[17px] font-bold">
              {t("manual.title")}
            </h2>
            <p className="m-0 text-base text-muted-foreground">{t("manual.hint")}</p>
          </div>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-3.5">
          <Input
            label={t("manual.description")}
            value={description}
            maxLength={255}
            placeholder={t("manual.descriptionPlaceholder")}
            onChange={(e) => {
              setDescription(e.target.value);
            }}
          />
          <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
            <Input
              type="date"
              label={t("manual.date")}
              value={spentOn}
              onChange={(e) => {
                setSpentOn(e.target.value);
              }}
            />
            <Input
              label={t("manual.amount")}
              value={amount}
              inputMode="decimal"
              maxLength={12}
              error={amountInvalid ? t("manual.amountInvalid") : undefined}
              onChange={(e) => {
                setAmount(e.target.value.replace(",", "."));
              }}
            />
            <Select
              label={t("manual.currency")}
              value={currency}
              onChange={(e) => {
                setCurrency(e.target.value);
              }}
            >
              {currencies.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
            <Select
              label={t("manual.category")}
              value={chosenCategory}
              onChange={(e) => {
                setCategoryId(e.target.value);
              }}
            >
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {categoryName(category.name)}
                </option>
              ))}
            </Select>
            <Select
              label={t("manual.kind")}
              value={kind}
              onChange={(e) => {
                setKind(KINDS.find((k) => k === e.target.value) ?? "");
              }}
            >
              <option value="">{t("manual.kindAuto")}</option>
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(`trips:spending.${k}`)}
                </option>
              ))}
            </Select>
          </div>
          {fromTrip && (
            <p className="m-0 text-md">{t("trips:question.fromTrip", { name: fromTrip.name })}</p>
          )}
          {trip && (
            <TripChoiceField
              trip={trip}
              answer={answer}
              onAnswer={(intoTrip) => {
                setAnswers({ ...answers, [trip.id]: intoTrip });
              }}
              className="rounded-control border border-border px-3 py-3"
            />
          )}
        </ModalBody>
        <ModalFooter>
          <span className="hidden md:block" />
          <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
            <Button type="button" variant="ghost" onClick={onClose}>
              {t("common:cancel")}
            </Button>
            <Button type="submit" disabled={!ready || saving}>
              {t("manual.save")}
            </Button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
});
