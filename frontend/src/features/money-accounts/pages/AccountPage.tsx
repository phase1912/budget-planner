import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowRight, ChevronLeft, ChevronRight, Lock, Pencil, Plus } from "lucide-react";

import { dateFormat } from "@/i18n/format";
import { BackLink, Button, ErrorState, LoadingState } from "@/shared/components";
import type { AccountEntry } from "@/stores/BankAccountsStore";
import { useStores } from "@/stores/StoreContext";
import { WHOLE, rateText } from "../accountFormat";
import { AccountDialog } from "../components/AccountDialog";
import { EntryDialog } from "../components/EntryDialog";
import { MoneyInDialog } from "../components/MoneyInDialog";
import { MoveDialog } from "../components/MoveDialog";
import { RuleDialog, type Rule } from "../components/RuleDialog";

const DAY = dateFormat({ day: "numeric", month: "short" });
const MONTH = dateFormat({ month: "long", year: "numeric" });

type Open = "in" | "move" | "edit" | "rule" | null;

function shiftMonth(month: string, by: number): string {
  const [year, m] = month.split("-").map(Number) as [number, number];
  const date = new Date(year, m - 1 + by, 1);
  return `${String(date.getFullYear())}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

/**
 * One account (F23.15, canvas F_Account, F_Rules, F_Check): what is on it and what of it
 * is set aside for taxes, money in and moves, what goes in or out of it every month by
 * itself, and its history month by month — this month's lines can be changed, earlier
 * months are closed, as on a bank statement.
 */
export const AccountPage = observer(function AccountPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { bankAccountsStore, budgetStore, incomeStore, householdStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const today = budgetStore.today;
  const thisMonth = today.slice(0, 7);
  const [month, setMonth] = useState(thisMonth);
  const [open, setOpen] = useState<Open>(null);
  const [rule, setRule] = useState<Rule | null>(null);
  const [entry, setEntry] = useState<AccountEntry | null>(null);
  const currency = authStore.user?.currency ?? "PLN";

  useEffect(() => {
    void bankAccountsStore.loadHistory(id, month, today);
  }, [bankAccountsStore, id, month, today]);
  useEffect(() => {
    if (!bankAccountsStore.loaded) void bankAccountsStore.load(today);
    void bankAccountsStore.loadTransfers();
    void incomeStore.loadRegular();
    void incomeStore.loadBills();
    if (!householdStore.loaded) void householdStore.load();
  }, [bankAccountsStore, incomeStore, householdStore, today]);

  const history = bankAccountsStore.history?.account.id === id ? bankAccountsStore.history : null;
  if (!history) {
    return bankAccountsStore.historyState.error ? (
      <ErrorState
        layout="banner"
        title={t("title")}
        message={bankAccountsStore.historyState.error}
      />
    ) : (
      <LoadingState title={t("title")} />
    );
  }

  const account = history.account;
  // A child sees the family's accounts and moves nothing on them (F12.10).
  const readOnly = account.shared && householdStore.isChild;
  const nameOf = (accountId: string) => bankAccountsStore.byId(accountId)?.name ?? "—";
  const when = (day: number | null | undefined) =>
    day == null ? t("rule.anyTime") : day === 31 ? t("rule.lastDay") : t("rule.onDay", { day });
  const rules: { key: string; rule: Rule; name: string; line: string; amount: string }[] = [
    ...incomeStore.regular
      .filter((r) => r.account_id === id)
      .map((r) => ({
        key: `i${r.id}`,
        rule: { kind: "income" as const, rule: r },
        name: r.name,
        line: t(r.about ? "rule.aboutLine" : "rule.incomeLine", { when: when(r.day) }),
        amount: `${r.about ? "≈ " : "+"}${WHOLE.format(Number(r.amount))} ${currency}`,
      })),
    ...incomeStore.bills
      .filter((b) => b.account_id === id)
      .map((b) => ({
        key: `b${b.id}`,
        rule: { kind: "bill" as const, rule: b },
        name: b.name,
        line: t("rule.billLine", { when: when(b.day) }),
        amount: `−${WHOLE.format(Number(b.amount))} ${currency}`,
      })),
    ...bankAccountsStore.transfers
      .filter((r) => r.from_account_id === id || r.to_account_id === id)
      .map((r) => {
        const out = r.from_account_id === id;
        return {
          key: `t${r.id}`,
          rule: { kind: "transfer" as const, rule: r },
          name: r.name,
          line: out
            ? t("rule.outLine", { name: nameOf(r.to_account_id), when: when(r.day) })
            : t("rule.inLine", { name: nameOf(r.from_account_id), when: when(r.day) }),
          amount: `${out ? "→ " : "← "}${WHOLE.format(Number(r.amount))} ${currency}`,
        };
      }),
  ];

  const sub = (e: AccountEntry) =>
    [
      e.kind === "purchases"
        ? e.author === "private"
          ? t("entry.privateNote")
          : [e.author, t("entry.receipts", { count: e.count })].filter(Boolean).join(" · ")
        : e.kind === "income" && Number(e.tax) > 0
          ? t("entry.incomeTax", { amount: WHOLE.format(Number(e.tax)) })
          : t(`entry.${e.kind}`),
      e.by_rule && e.kind !== "expected" ? t("entry.byRule") : null,
      e.upcoming ? t("entry.upcoming") : null,
    ]
      .filter(Boolean)
      .join(" · ");
  const lineName = (e: AccountEntry) =>
    e.kind === "purchases"
      ? e.author === "private"
        ? t("entry.private")
        : t("entry.purchases")
      : e.kind === "tax_paid"
        ? t("entry.taxes")
        : e.kind === "adjustment"
          ? t("entry.correction")
          : e.name;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 py-4 md:gap-5 md:py-2">
      <div className="flex items-center gap-3">
        <BackLink to="/accounts" label={t("back")} />
        <h1 className="m-0 min-w-0 truncate text-3xl font-extrabold tracking-[-0.02em]">
          {account.name}
        </h1>
        {account.shared && (
          <span className="shrink-0 rounded-pill bg-tone-primary-bg px-2 py-0.5 text-xs font-extrabold text-primary">
            {t("shared")}
          </span>
        )}
      </div>

      <section className="flex flex-col gap-1 rounded-hero bg-surface p-5 md:p-6">
        <span className="text-md font-semibold text-muted-foreground">{t("onIt")}</span>
        <span className="text-4xl font-extrabold tabular-nums">
          {WHOLE.format(Number(account.balance))} {currency}
        </span>
        {account.kind === "business" && Number(account.tax_rate ?? 0) > 0 && (
          <span className="text-md font-semibold text-tone-warning-text tabular-nums">
            {t("tax", {
              rate: rateText(account.tax_rate),
              amount: WHOLE.format(Number(account.set_aside)),
              currency,
            })}
          </span>
        )}
        {!readOnly && (
          <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-3">
            <Button
              className="col-span-2 min-h-11 px-2 md:col-span-1"
              onClick={() => {
                setOpen("in");
              }}
            >
              <Plus size={18} aria-hidden="true" />
              {t("moneyIn")}
            </Button>
            <Button
              variant="secondary"
              className="min-h-11 px-2"
              disabled={bankAccountsStore.accounts.length < 2}
              onClick={() => {
                setOpen("move");
              }}
            >
              <ArrowRight size={18} aria-hidden="true" />
              {t("moveShort")}
            </Button>
            <Button
              variant="secondary"
              className="min-h-11 px-2"
              onClick={() => {
                setOpen("edit");
              }}
            >
              <Pencil size={16} aria-hidden="true" />
              {t("edit")}
            </Button>
          </div>
        )}
      </section>

      {account.kind !== "deposit" && (
        <section
          aria-labelledby="every-month"
          className="flex flex-col gap-3 rounded-hero bg-surface p-4 md:p-6"
        >
          <h2 id="every-month" className="m-0 text-xl font-extrabold">
            {t("every")}
          </h2>
          {rules.length === 0 ? (
            <p className="m-0 text-md text-muted-foreground">{t("noRules")}</p>
          ) : (
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {rules.map((r) => (
                <li key={r.key}>
                  <button
                    type="button"
                    disabled={readOnly}
                    onClick={() => {
                      setRule(r.rule);
                      setOpen("rule");
                    }}
                    className="control-fill flex min-h-14 w-full items-center gap-3 rounded-card px-3.5 py-2.5 text-left"
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-lg font-bold">{r.name}</span>
                      <span className="text-md text-muted-foreground">{r.line}</span>
                    </span>
                    <span className="shrink-0 text-lg font-extrabold tabular-nums">{r.amount}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {!readOnly && (
            <button
              type="button"
              onClick={() => {
                setRule(null);
                setOpen("rule");
              }}
              className="flex min-h-11 items-center gap-2 self-start text-left text-lg font-bold text-primary"
            >
              <Plus size={18} aria-hidden="true" className="shrink-0" />
              {t("addRule")}
            </button>
          )}
        </section>
      )}

      <section
        aria-labelledby="history"
        className="flex flex-col gap-3 rounded-hero bg-surface p-4 md:p-6"
      >
        <div className="flex items-center justify-between gap-2">
          <h2 id="history" className="m-0 text-xl font-extrabold">
            {t("history")}
          </h2>
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label={t("previous")}
              className="control-fill flex h-11 w-11 items-center justify-center rounded-pill"
              onClick={() => {
                setMonth(shiftMonth(month, -1));
              }}
            >
              <ChevronLeft size={18} aria-hidden="true" />
            </button>
            <span className="min-w-28 text-center text-md font-bold capitalize">
              {MONTH.format(new Date(`${month}-01T00:00:00`))}
            </span>
            <button
              type="button"
              aria-label={t("next")}
              disabled={month >= thisMonth}
              className="control-fill flex h-11 w-11 items-center justify-center rounded-pill disabled:opacity-40"
              onClick={() => {
                setMonth(shiftMonth(month, 1));
              }}
            >
              <ChevronRight size={18} aria-hidden="true" />
            </button>
          </div>
        </div>
        {history.entries.length === 0 ? (
          <p className="m-0 text-md text-muted-foreground">{t("noHistory")}</p>
        ) : (
          <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
            {history.entries.map((e, i) => {
              const positive = Number(e.amount) > 0;
              const faded = e.upcoming || e.kind === "expected";
              const editable = e.editable && !readOnly;
              const content = (
                <>
                  <span className="hidden w-16 shrink-0 text-md font-semibold text-muted-foreground tabular-nums md:block">
                    {DAY.format(new Date(`${e.day}T00:00:00`))}
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-lg font-bold">{lineName(e)}</span>
                    <span className="text-md text-muted-foreground">
                      {/* On a phone the day leads the line under the name, not a column. */}
                      <span className="tabular-nums md:hidden">
                        {DAY.format(new Date(`${e.day}T00:00:00`))} ·{" "}
                      </span>
                      {sub(e)}
                    </span>
                  </span>
                  <span
                    className={`shrink-0 text-lg font-extrabold tabular-nums ${
                      e.kind === "transfer_in" || e.kind === "transfer_out"
                        ? "text-muted-foreground"
                        : positive
                          ? "text-primary"
                          : "text-foreground"
                    }`}
                  >
                    {e.kind === "expected" ? "≈ " : positive ? "+" : "−"}
                    {WHOLE.format(Math.abs(Number(e.amount)))} {currency}
                  </span>
                  {history.closed ? (
                    <Lock size={14} aria-hidden="true" className="shrink-0 text-muted-foreground" />
                  ) : editable ? (
                    <Pencil
                      size={14}
                      aria-hidden="true"
                      className="shrink-0 text-muted-foreground"
                    />
                  ) : (
                    <span className="w-3.5 shrink-0" />
                  )}
                </>
              );
              return (
                <li
                  key={`${e.ref_id ?? e.kind}-${e.day}-${String(i)}`}
                  className={faded ? "opacity-60" : ""}
                >
                  {editable ? (
                    <button
                      type="button"
                      onClick={() => {
                        setEntry(e);
                      }}
                      className="flex min-h-14 w-full items-center gap-3 py-2 text-left"
                    >
                      {content}
                    </button>
                  ) : (
                    <div className="flex min-h-14 items-center gap-3 py-2">{content}</div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <p className="m-0 text-sm text-muted-foreground">
          {history.closed ? t("closed") : t("closedNote")}
        </p>
      </section>

      {open === "in" && (
        <MoneyInDialog
          account={account}
          today={today}
          onClose={() => {
            setOpen(null);
          }}
        />
      )}
      {open === "move" && (
        <MoveDialog
          fromId={account.id}
          today={today}
          onClose={() => {
            setOpen(null);
          }}
        />
      )}
      {open === "edit" && (
        <AccountDialog
          account={account}
          today={today}
          onClose={() => {
            setOpen(null);
          }}
          onDeleted={() => {
            void navigate("/accounts");
          }}
        />
      )}
      {open === "rule" && (
        <RuleDialog
          account={account}
          editing={rule}
          today={today}
          onClose={() => {
            setOpen(null);
          }}
        />
      )}
      {entry && (
        <EntryDialog
          entry={entry}
          today={today}
          onClose={() => {
            setEntry(null);
          }}
        />
      )}
    </div>
  );
});
