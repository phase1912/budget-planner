import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Select } from "@/shared/components";
import type { ExpectedIncome } from "@/stores/BankAccountsStore";
import type { PendingIncome } from "@/stores/IncomeStore";
import { useStores } from "@/stores/StoreContext";
import { WHOLE, typedAmount } from "../accountFormat";

/**
 * "To check" (F23.15, canvas F_Check): "about" incomes whose day has come, confirmed with
 * what really came — more is a bonus counted this month only — and income read from
 * email, put on the account it reached.
 */
export const ToCheck = observer(function ToCheck({ today }: { today: string }) {
  const { bankAccountsStore, incomeStore } = useStores();
  const { t } = useTranslation("accounts");
  if (bankAccountsStore.expected.length === 0 && incomeStore.pending.length === 0) return null;

  return (
    <section aria-labelledby="to-check" className="flex flex-col gap-3">
      <h2 id="to-check" className="m-0 text-xl font-extrabold">
        {t("check.title")}
      </h2>
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {bankAccountsStore.expected.map((item) => (
          <li key={item.source_id}>
            <Expected item={item} today={today} />
          </li>
        ))}
        {incomeStore.pending.map((item) => (
          <li key={item.id}>
            <FromEmail item={item} today={today} />
          </li>
        ))}
      </ul>
    </section>
  );
});

const Expected = observer(function Expected({
  item,
  today,
}: {
  item: ExpectedIncome;
  today: string;
}) {
  const { bankAccountsStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const currency = authStore.user?.currency ?? "PLN";
  const account = bankAccountsStore.byId(item.account_id);
  const [text, setText] = useState(String(Number(item.amount)));
  const [hidden, setHidden] = useState(false);
  const amount = typedAmount(text);
  const delta = amount === null ? 0 : Number(amount) - Number(item.amount);
  if (hidden) return null;

  return (
    <div className="flex flex-col gap-3 rounded-card bg-surface p-4">
      <span className="text-md font-semibold text-muted-foreground">
        {t("check.expected", { account: account?.name ?? "" })}
      </span>
      <span className="text-lg font-extrabold">
        {item.name} · ≈ {WHOLE.format(Number(item.amount))} {currency}
      </span>
      <Input
        label={t("check.actual", { currency })}
        inputMode="decimal"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
        }}
      />
      {Math.abs(delta) >= 1 && (
        <p className={`m-0 text-md ${delta > 0 ? "text-primary" : "text-tone-warning-text"}`}>
          {delta > 0
            ? t("check.more", { amount: WHOLE.format(delta), currency })
            : t("check.less", { amount: WHOLE.format(-delta), currency })}
        </p>
      )}
      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="secondary"
          className="min-h-11"
          onClick={() => {
            setHidden(true);
          }}
        >
          {t("check.notYet")}
        </Button>
        <Button
          className="min-h-11"
          disabled={amount === null || bankAccountsStore.saveState.isLoading}
          onClick={() => {
            if (amount !== null) void bankAccountsStore.confirm(item.source_id, amount, today);
          }}
        >
          {t("check.came")}
        </Button>
      </div>
    </div>
  );
});

const FromEmail = observer(function FromEmail({
  item,
  today,
}: {
  item: PendingIncome;
  today: string;
}) {
  const { bankAccountsStore, incomeStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const currency = authStore.user?.currency ?? "PLN";
  const accounts = bankAccountsStore.accounts;
  const [accountId, setAccountId] = useState(
    accounts.find((a) => a.kind === "business")?.id ?? accounts[0]?.id ?? "",
  );
  const [text, setText] = useState(item.amount == null ? "" : String(Number(item.amount)));
  const amount = typedAmount(text);
  const account = bankAccountsStore.byId(accountId);

  return (
    <div className="flex flex-col gap-3 rounded-card bg-surface p-4">
      <span className="text-md font-semibold text-muted-foreground">{t("check.email")}</span>
      <span className="text-lg font-extrabold">{item.source ?? "—"}</span>
      <Input
        label={t("in.amount", { currency })}
        inputMode="decimal"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
        }}
      />
      <Select
        label={t("check.which")}
        value={accountId}
        onChange={(e) => {
          setAccountId(e.target.value);
        }}
      >
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </Select>
      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="secondary"
          className="min-h-11"
          onClick={() => void incomeStore.dismissPending(item.id)}
        >
          {t("check.dismiss")}
        </Button>
        <Button
          className="min-h-11"
          disabled={amount === null || accountId === "" || incomeStore.saveState.isLoading}
          onClick={() => {
            if (amount === null) return;
            void incomeStore
              .confirmPending(item.id, {
                amount,
                received_on: item.received_on ?? today,
                source: item.source ?? t("check.email"),
                kind: account?.kind === "business" ? "side" : item.kind,
                shared: account?.shared ?? false,
                account_id: accountId,
              })
              .then((ok) => {
                if (ok) void bankAccountsStore.load(today);
              });
          }}
        >
          {t("check.save")}
        </Button>
      </div>
    </div>
  );
});
