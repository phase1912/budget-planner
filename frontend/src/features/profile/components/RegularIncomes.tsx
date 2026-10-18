import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button, Input, Select, Switch } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import type { RegularBill, RegularIncome } from "@/stores/IncomeStore";
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
 * Regular incomes or regular bills, edited in place (F23.17, F23.18): a salary, a side
 * job, a pension — or rent, a subscription — each counted every month by itself from now
 * on. For one who pays their own taxes, an income says whether the tax comes out of it
 * (F23.16). Used in Settings, Plan and the first-sign-in setup.
 */
export const RegularIncomes = observer(function RegularIncomes({
  currency: chosenCurrency,
  kind = "income",
}: {
  /** The currency being chosen, before it is saved — in the first-sign-in setup. */
  currency?: string;
  kind?: "income" | "bill";
}) {
  const { incomeStore, authStore } = useStores();
  const { t } = useTranslation("profile");
  const currency = chosenCurrency ?? authStore.user?.currency ?? "PLN";
  const bill = kind === "bill";
  const paysOwnTaxes = !bill && authStore.user?.pays_own_taxes === true;
  const words = bill ? "bills" : "regular";
  const items: (RegularIncome | RegularBill)[] = bill ? incomeStore.bills : incomeStore.regular;
  // The id of the income open for changes, "new" for one being added, or null.
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);

  useEffect(() => {
    void (bill ? incomeStore.loadBills() : incomeStore.loadRegular());
  }, [incomeStore, bill]);

  const amount = draft.amount.trim().replace(",", ".").replace(/\s/g, "");
  const valid = draft.name.trim() !== "" && /^\d+(\.\d{1,2})?$/.test(amount) && Number(amount) > 0;
  const open = (income: RegularIncome | RegularBill | null) => {
    setEditing(income?.id ?? "new");
    setDraft(
      income
        ? {
            name: income.name,
            amount: income.amount,
            day: income.day == null ? "" : String(income.day),
            taxed: "taxed" in income && income.taxed,
          }
        : EMPTY,
    );
  };
  const save = async () => {
    const base = { name: draft.name.trim(), amount, day: draft.day ? Number(draft.day) : null };
    const today = isoDay(new Date());
    const ok = bill
      ? editing === "new"
        ? await incomeStore.addBill(base, today)
        : await incomeStore.changeBill(editing ?? "", base)
      : editing === "new"
        ? await incomeStore.addRegular({ ...base, taxed: draft.taxed }, today)
        : await incomeStore.changeRegular(editing ?? "", { ...base, taxed: draft.taxed });
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
        label={t(`${words}.name`)}
        placeholder={t(`${words}.namePlaceholder`)}
        value={draft.name}
        maxLength={80}
        onChange={(e) => {
          setDraft((d) => ({ ...d, name: e.target.value }));
        }}
      />
      <div className="grid grid-cols-2 gap-3">
        <Input
          label={t(`${words}.amount`, { currency })}
          inputMode="decimal"
          value={draft.amount}
          onChange={(e) => {
            setDraft((d) => ({ ...d, amount: e.target.value }));
          }}
        />
        <Select
          label={t(`${words}.day`)}
          value={draft.day}
          onChange={(e) => {
            setDraft((d) => ({ ...d, day: e.target.value }));
          }}
        >
          <option value="">{t(`${words}.anyDay`)}</option>
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
              const today = isoDay(new Date());
              void (
                bill ? incomeStore.endBill(editing, today) : incomeStore.endRegular(editing, today)
              ).then((ok) => {
                if (ok) setEditing(null);
              });
            }}
          >
            {t(`${words}.remove`)}
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
            {t(`${words}.cancel`)}
          </Button>
          <Button type="submit" size="sm" className="min-h-11" disabled={!valid}>
            {t(`${words}.save`)}
          </Button>
        </div>
      </div>
    </form>
  );

  return (
    <div className="flex flex-col gap-2.5">
      {items.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {items.map((income) =>
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
                          ? t(`${words}.monthly`)
                          : income.day === 31
                            ? t("money.lastDay")
                            : t(`${words}.onDay`, { day: income.day }),
                        paysOwnTaxes && "taxed" in income && income.taxed
                          ? t("regular.taxedShort")
                          : null,
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
          {items.length === 0 ? t(`${words}.addFirst`) : t(`${words}.add`)}
        </button>
      )}
    </div>
  );
});
