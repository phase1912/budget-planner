import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button, Input, Select, Switch } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import type { RegularIncome } from "@/stores/IncomeStore";
import { isoDay } from "@/stores/StatisticsStore";
import { useStores } from "@/stores/StoreContext";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAYS = Array.from({ length: 30 }, (_, i) => i + 1);

interface Draft {
  name: string;
  amount: string;
  day: string;
  taxed: boolean;
}

const EMPTY: Draft = { name: "", amount: "", day: "", taxed: false };

/**
 * The regular incomes, edited in place (F23.17): a salary, a side job, a pension — each
 * counted every month by itself from now on. For one who pays their own taxes, each says
 * whether the tax comes out of it (F23.16). Used in Settings and in the first-sign-in setup.
 */
export const RegularIncomes = observer(function RegularIncomes({
  currency: chosenCurrency,
}: {
  /** The currency being chosen, before it is saved — in the first-sign-in setup. */
  currency?: string;
}) {
  const { incomeStore, authStore } = useStores();
  const { t } = useTranslation("profile");
  const currency = chosenCurrency ?? authStore.user?.currency ?? "PLN";
  const paysOwnTaxes = authStore.user?.pays_own_taxes === true;
  // The id of the income open for changes, "new" for one being added, or null.
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);

  useEffect(() => {
    void incomeStore.loadRegular();
  }, [incomeStore]);

  const amount = draft.amount.trim().replace(",", ".").replace(/\s/g, "");
  const valid = draft.name.trim() !== "" && /^\d+(\.\d{1,2})?$/.test(amount) && Number(amount) > 0;
  const open = (income: RegularIncome | null) => {
    setEditing(income?.id ?? "new");
    setDraft(
      income
        ? {
            name: income.name,
            amount: income.amount,
            day: income.day == null ? "" : String(income.day),
            taxed: income.taxed,
          }
        : EMPTY,
    );
  };
  const save = async () => {
    const body = {
      name: draft.name.trim(),
      amount,
      day: draft.day ? Number(draft.day) : null,
      taxed: draft.taxed,
    };
    const ok =
      editing === "new"
        ? await incomeStore.addRegular(body, isoDay(new Date()))
        : await incomeStore.changeRegular(editing ?? "", body);
    if (ok) setEditing(null);
  };

  const form = (
    <form
      className="flex flex-col gap-3 rounded-card control-fill p-3.5"
      onSubmit={(event) => {
        event.preventDefault();
        if (valid) void save();
      }}
    >
      <Input
        label={t("regular.name")}
        placeholder={t("regular.namePlaceholder")}
        value={draft.name}
        maxLength={80}
        onChange={(e) => {
          setDraft((d) => ({ ...d, name: e.target.value }));
        }}
      />
      <div className="grid grid-cols-2 gap-3">
        <Input
          label={t("regular.amount", { currency })}
          inputMode="decimal"
          value={draft.amount}
          onChange={(e) => {
            setDraft((d) => ({ ...d, amount: e.target.value }));
          }}
        />
        <Select
          label={t("regular.day")}
          value={draft.day}
          onChange={(e) => {
            setDraft((d) => ({ ...d, day: e.target.value }));
          }}
        >
          <option value="">{t("regular.anyDay")}</option>
          {DAYS.map((day) => (
            <option key={day} value={day}>
              {day}
            </option>
          ))}
          <option value="31">{t("money.lastDay")}</option>
        </Select>
      </div>
      {paysOwnTaxes && (
        <Switch
          checked={draft.taxed}
          onChange={(value) => {
            setDraft((d) => ({ ...d, taxed: value }));
          }}
          label={t("regular.taxed")}
          ariaLabel={t("regular.taxed")}
        />
      )}
      <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-between">
        {editing !== "new" && editing !== null ? (
          <Button
            type="button"
            variant="danger"
            size="sm"
            className="min-h-11"
            onClick={() => {
              void incomeStore.endRegular(editing, isoDay(new Date())).then((ok) => {
                if (ok) setEditing(null);
              });
            }}
          >
            {t("regular.remove")}
          </Button>
        ) : (
          <span />
        )}
        <div className="flex gap-2 [&>*]:flex-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="min-h-11"
            onClick={() => {
              setEditing(null);
            }}
          >
            {t("regular.cancel")}
          </Button>
          <Button type="submit" size="sm" className="min-h-11" disabled={!valid}>
            {t("regular.save")}
          </Button>
        </div>
      </div>
    </form>
  );

  return (
    <div className="flex flex-col gap-2.5">
      {incomeStore.regular.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {incomeStore.regular.map((income) =>
            editing === income.id ? (
              <li key={income.id}>{form}</li>
            ) : (
              <li key={income.id}>
                <button
                  type="button"
                  onClick={() => {
                    open(income);
                  }}
                  className="control-fill flex min-h-14 w-full items-center gap-3 rounded-card px-3.5 py-2.5 text-left"
                >
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-lg font-bold">{income.name}</span>
                    <span className="text-md text-muted-foreground">
                      {[
                        income.day == null
                          ? t("regular.monthly")
                          : income.day === 31
                            ? t("money.lastDay")
                            : t("regular.onDay", { day: income.day }),
                        paysOwnTaxes && income.taxed ? t("regular.taxedShort") : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </span>
                  <span className="shrink-0 text-lg font-extrabold tabular-nums">
                    {WHOLE.format(Number(income.amount))} {currency}
                  </span>
                </button>
              </li>
            ),
          )}
        </ul>
      )}
      {editing === "new" ? (
        form
      ) : (
        <button
          type="button"
          onClick={() => {
            open(null);
          }}
          className="flex min-h-11 items-center gap-2 text-lg font-bold text-primary"
        >
          <Plus size={18} aria-hidden="true" />
          {incomeStore.regular.length === 0 ? t("regular.addFirst") : t("regular.add")}
        </button>
      )}
    </div>
  );
});
