import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { Pencil, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Button,
  Input,
  RepeatField,
  Switch,
  useRepeatLabel,
  type Repeat,
} from "@/shared/components";
import { NewCardFields } from "@/features/money-accounts/components/NewCardFields";
import {
  newCardBody,
  useCardName,
  type NewCard,
} from "@/features/money-accounts/components/newCard";
import { numberFormat } from "@/i18n/format";
import type { RegularBill, RegularIncome } from "@/stores/IncomeStore";
import { isoDay } from "@/stores/StatisticsStore";
import { useStores } from "@/stores/StoreContext";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });

interface Draft {
  name: string;
  amount: string;
  repeat: Repeat;
  taxed: boolean;
  shared: boolean;
}

const EMPTY: Draft = {
  name: "",
  amount: "",
  repeat: { day: null, weekday: null },
  taxed: false,
  shared: false,
};

/**
 * Regular incomes or regular bills, edited in place (F23.17, F23.18): a salary, a side
 * job, a pension — or rent, a subscription — each counted by itself from now on, monthly
 * on a day or weekly on a weekday (F23.21). A first income with no card yet makes the
 * card it lands on; a bill needs none. For one who pays their own taxes, an income says whether the tax comes out of it
 * (F23.16). Inside a household each one is the family's or the user's own (F12.8): a
 * shared bill is the family's whole, never divided, and a row another member added says
 * who. Used in Settings, Plan and the first-sign-in setup: a row opens
 * for changes in place, with Stop beside Save, so nothing else has to be opened.
 */
export const RegularIncomes = observer(function RegularIncomes({
  currency: chosenCurrency,
  kind = "income",
  onChanged,
  hideAdd = false,
  onPending,
}: {
  /** The currency being chosen, before it is saved — in the first-sign-in setup. */
  currency?: string;
  kind?: "income" | "bill";
  /** Called after one is added, changed or stopped — Plan refreshes the month's figures. */
  onChanged?: () => void;
  /** Plan adds incomes through its one dialog (F23.15): the list only shows and changes. */
  hideAdd?: boolean;
  /**
   * Hands the screen around a way to finish an open form — saved if filled in, dropped if
   * blank, refused if half done — so a step's own Next never throws a typed income away.
   */
  onPending?: (finish: (() => Promise<boolean>) | null) => void;
}) {
  const { incomeStore, authStore, householdStore, bankAccountsStore } = useStores();
  // With accounts, whose a sum is follows its account (F23.15): no separate choice.
  const withAccounts = bankAccountsStore.accounts.length > 0;
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
  const repeatLabel = useRepeatLabel();
  const cardName = useCardName();
  // Income is bookkeeping (F23.21): with no card yet, the first one makes it.
  const needsCard = !bill && !withAccounts;
  const [card, setCard] = useState<NewCard>({ name: "", opening: "" });
  const newCard = needsCard ? newCardBody(card) : null;

  useEffect(() => {
    void (bill ? incomeStore.loadBills() : incomeStore.loadRegular());
  }, [incomeStore, bill]);

  // Whose each one is depends on the household, which Plan and Settings do not load.
  useEffect(() => {
    if (!householdStore.loaded) void householdStore.load();
  }, [householdStore]);

  const amount = draft.amount.trim().replace(",", ".").replace(/\s/g, "");
  const valid =
    draft.name.trim() !== "" &&
    /^\d+(\.\d{1,2})?$/.test(amount) &&
    Number(amount) > 0 &&
    (!needsCard || newCard !== null);
  const open = (income: RegularIncome | RegularBill | null) => {
    setEditing(income?.id ?? "new");
    setDraft(
      income
        ? {
            name: income.name,
            amount: income.amount,
            repeat: { day: income.day ?? null, weekday: income.weekday ?? null },
            taxed: "taxed" in income && income.taxed,
            shared: income.shared,
          }
        : // A new one in a household is the family's unless the user says otherwise.
          { ...EMPTY, shared: mayShare },
    );
    setCard({ name: cardName(mayShare), opening: "" });
  };
  // Asked to finish with the form only half filled in: say what is missing.
  const [tried, setTried] = useState(false);
  const save = async (): Promise<boolean> => {
    // A change keeps the account it is on and whether it varies (F23.15).
    const original = items.find((i) => i.id === editing);
    const base = {
      name: draft.name.trim(),
      amount,
      day: draft.repeat.day,
      weekday: draft.repeat.weekday,
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
        ? await incomeStore.addRegular(
            { ...base, taxed: draft.taxed, about: false, new_card: newCard },
            today,
          )
        : await incomeStore.changeRegular(editing ?? "", {
            ...base,
            taxed: draft.taxed,
            about,
            new_card: newCard,
          });
    if (!ok) return false;
    // A first income made its card on the server: the screens listing cards see it now.
    if (newCard) await bankAccountsStore.load(today);
    setEditing(null);
    onChanged?.();
    return true;
  };
  const finish = useRef<() => Promise<boolean>>(() => Promise.resolve(true));
  finish.current = () => {
    if (editing === null) return Promise.resolve(true);
    if (draft.name.trim() === "" && amount === "") {
      setEditing(null);
      return Promise.resolve(true);
    }
    if (!valid) {
      setTried(true);
      return Promise.resolve(false);
    }
    return save();
  };
  useEffect(() => {
    onPending?.(() => finish.current());
    return () => {
      onPending?.(null);
    };
  }, [onPending]);

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
      <Input
        label={t(`${words}.amount`, { currency })}
        inputMode="decimal"
        value={draft.amount}
        onChange={(e) => {
          setDraft((d) => ({ ...d, amount: e.target.value }));
        }}
      />
      <RepeatField
        value={draft.repeat}
        onChange={(repeat) => {
          setDraft((d) => ({ ...d, repeat }));
        }}
      />
      {needsCard && <NewCardFields value={card} onChange={setCard} currency={currency} />}
      {tried && !valid && (
        <p role="alert" className="m-0 text-md text-tone-error-text">
          {t(`${words}.incomplete`)}
        </p>
      )}
      {mayShare && !withAccounts && (
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
                        repeatLabel({ day: income.day ?? null, weekday: income.weekday ?? null }),
                        paysOwnTaxes && "taxed" in income && income.taxed
                          ? t("regular.taxedShort")
                          : null,
                        income.account_id && bankAccountsStore.byId(income.account_id)
                          ? t("onAccount", {
                              name: bankAccountsStore.byId(income.account_id)?.name,
                            })
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
      ) : hideAdd ? null : (
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
