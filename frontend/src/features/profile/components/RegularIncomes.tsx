import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Pencil, Plus } from "lucide-react";
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
  shared: boolean;
}

const EMPTY: Draft = { name: "", amount: "", day: "", taxed: false, shared: false };

/**
 * Regular incomes or regular bills, edited in place (F23.17, F23.18): a salary, a side
 * job, a pension — or rent, a subscription — each counted every month by itself from now
 * on. For one who pays their own taxes, an income says whether the tax comes out of it
 * (F23.16). Inside a household each one is the family's or the user's own (F12.8): a
 * shared bill is the family's whole, never divided, and a row another member added says
 * who. Used in Settings, Plan and the first-sign-in setup: a row opens
 * for changes in place, with Stop beside Save, so nothing else has to be opened.
 */
export const RegularIncomes = observer(function RegularIncomes({
  currency: chosenCurrency,
  kind = "income",
  onChanged,
}: {
  /** The currency being chosen, before it is saved — in the first-sign-in setup. */
  currency?: string;
  kind?: "income" | "bill";
  /** Called after one is added, changed or stopped — Plan refreshes the month's figures. */
  onChanged?: () => void;
}) {
  const { incomeStore, authStore, householdStore } = useStores();
  const inHousehold = householdStore.household !== null;
  const mayShare = householdStore.mayShare;
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

  // Whose each one is depends on the household, which Plan and Settings do not load.
  useEffect(() => {
    if (!householdStore.loaded) void householdStore.load();
  }, [householdStore]);

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
            shared: income.shared,
          }
        : // A new one in a household is the family's unless the user says otherwise.
          { ...EMPTY, shared: mayShare },
    );
  };
  const save = async () => {
    // A change keeps the account it is on and whether it varies (F23.15).
    const original = items.find((i) => i.id === editing);
    const base = {
      name: draft.name.trim(),
      amount,
      day: draft.day ? Number(draft.day) : null,
      shared: mayShare && draft.shared,
      account_id: original?.account_id ?? null,
    };
    const about = original !== undefined && "about" in original && original.about;
    const today = isoDay(new Date());
    const ok = bill
      ? editing === "new"
        ? await incomeStore.addBill(base, today)
        : await incomeStore.changeBill(editing ?? "", base)
      : editing === "new"
        ? await incomeStore.addRegular({ ...base, taxed: draft.taxed, about: false }, today)
        : await incomeStore.changeRegular(editing ?? "", { ...base, taxed: draft.taxed, about });
    if (!ok) return;
    setEditing(null);
    onChanged?.();
  };

  const form = (
    <form
      className="flex flex-col gap-3 rounded-card border-2 border-primary p-3.5"
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
      {mayShare && (
        <div className="flex flex-col gap-2">
          <span className="text-md font-semibold text-muted-foreground">{t("whose.title")}</span>
          <div role="radiogroup" aria-label={t("whose.title")} className="grid grid-cols-2 gap-2">
            {([true, false] as const).map((shared) => (
              <button
                key={String(shared)}
                type="button"
                role="radio"
                aria-checked={draft.shared === shared}
                onClick={() => {
                  setDraft((d) => ({ ...d, shared }));
                }}
                className={`min-h-11 rounded-control border-2 px-3 text-md font-bold ${
                  draft.shared === shared ? "border-primary bg-tone-primary-bg" : "border-border"
                }`}
              >
                {shared ? t("whose.shared") : t("whose.onlyMine")}
              </button>
            ))}
          </div>
        </div>
      )}
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
                if (!ok) return;
                setEditing(null);
                onChanged?.();
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
                <Row
                  // A child sees the family's money and changes none of it (F12.10).
                  onOpen={
                    householdStore.isChild && income.shared
                      ? undefined
                      : () => {
                          open(income);
                        }
                  }
                >
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="truncate text-lg font-bold">{income.name}</span>
                      {inHousehold && (
                        <span
                          className={`shrink-0 rounded-pill px-2 py-0.5 text-xs font-extrabold ${
                            income.shared
                              ? "bg-tone-primary-bg text-primary"
                              : "bg-muted text-foreground"
                          }`}
                        >
                          {income.shared ? t("whose.sharedChip") : t("whose.mineChip")}
                        </span>
                      )}
                    </span>
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
                        income.added_by ? t("whose.addedBy", { name: income.added_by }) : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </span>
                  <span className="shrink-0 text-lg font-extrabold tabular-nums">
                    {WHOLE.format(Number(income.amount))} {currency}
                  </span>
                </Row>
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

/** One income or bill in the list: opens for changes, or only shows when it may not change. */
function Row({ onOpen, children }: { onOpen?: () => void; children: React.ReactNode }) {
  const className =
    "control-fill flex min-h-14 w-full items-center gap-3 rounded-card px-3.5 py-2.5 text-left";
  if (!onOpen) return <div className={className}>{children}</div>;
  return (
    <button type="button" onClick={onOpen} className={className}>
      {children}
      <Pencil size={15} aria-hidden="true" className="shrink-0 text-muted-foreground" />
    </button>
  );
}
