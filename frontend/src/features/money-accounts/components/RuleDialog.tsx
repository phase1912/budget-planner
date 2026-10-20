import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { dateFormat } from "@/i18n/format";
import { Button, Input, Modal, ModalBody, Select } from "@/shared/components";
import type { BankAccount, TransferRule } from "@/stores/BankAccountsStore";
import type { RegularBill, RegularIncome } from "@/stores/IncomeStore";
import { useStores } from "@/stores/StoreContext";
import { firstRun, typedAmount } from "../accountFormat";
import { Choice } from "./Choice";

const DATE = dateFormat({ day: "numeric", month: "long" });
const DAYS = Array.from({ length: 28 }, (_, i) => i + 1);

export type RuleKind = "income" | "bill" | "transfer";
export type Rule =
  | { kind: "income"; rule: RegularIncome }
  | { kind: "bill"; rule: RegularBill }
  | { kind: "transfer"; rule: TransferRule };

/**
 * Something that happens on an account every month by itself (F23.15, canvas F_Rules):
 * income that comes in — always the same, or about and confirmed each month — a bill
 * that goes, or a transfer to another account. It says when it first runs: this month,
 * or next month when its day has already passed. An existing one can be changed or
 * stopped from next month.
 */
export const RuleDialog = observer(function RuleDialog({
  account,
  editing,
  today,
  onClose,
}: {
  account: BankAccount;
  editing: Rule | null;
  today: string;
  onClose: () => void;
}) {
  const { bankAccountsStore, incomeStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const currency = authStore.user?.currency ?? "PLN";
  const others = bankAccountsStore.accounts.filter((a) => a.id !== account.id);
  const [kind, setKind] = useState<RuleKind>(
    editing?.kind ?? (account.kind === "business" ? "bill" : "income"),
  );
  const [name, setName] = useState(editing?.rule.name ?? "");
  const [amountText, setAmountText] = useState(editing ? String(Number(editing.rule.amount)) : "");
  const [day, setDay] = useState(editing?.rule.day == null ? "" : String(editing.rule.day));
  const [about, setAbout] = useState(editing?.kind === "income" && editing.rule.about);
  const [to, setTo] = useState(
    editing?.kind === "transfer" ? editing.rule.to_account_id : (others[0]?.id ?? ""),
  );
  const amount = typedAmount(amountText);
  const dayNumber = day === "" ? null : Number(day);
  const transfer = kind === "transfer";
  const valid =
    amount !== null && Number(amount) > 0 && (transfer ? to !== "" : name.trim() !== "");
  const busy = bankAccountsStore.saveState.isLoading || incomeStore.saveState.isLoading;
  const first = firstRun(dayNumber, new Date(`${today}T00:00:00`));

  const done = (ok: boolean) => {
    if (!ok) return;
    void bankAccountsStore.load(today);
    if (bankAccountsStore.history) {
      void bankAccountsStore.loadHistory(account.id, bankAccountsStore.history.month, today);
    }
    onClose();
  };

  const save = async () => {
    if (!valid) return;
    const shared = account.shared;
    if (kind === "income") {
      const body = {
        name: name.trim(),
        amount,
        day: dayNumber,
        taxed: false,
        shared,
        account_id: account.id,
        about,
      };
      done(
        editing?.kind === "income"
          ? await incomeStore.changeRegular(editing.rule.id, body)
          : await incomeStore.addRegular(body, today),
      );
    } else if (kind === "bill") {
      const body = { name: name.trim(), amount, day: dayNumber, shared, account_id: account.id };
      done(
        editing?.kind === "bill"
          ? await incomeStore.changeBill(editing.rule.id, body)
          : await incomeStore.addBill(body, today),
      );
    } else {
      const target = bankAccountsStore.byId(to);
      const body = {
        from_account_id: account.id,
        to_account_id: to,
        amount,
        day: dayNumber,
        name: name.trim() || (target ? `→ ${target.name}` : null),
      };
      done(
        editing?.kind === "transfer"
          ? await bankAccountsStore.changeTransfer(editing.rule.id, body, today)
          : await bankAccountsStore.addTransfer(body, today),
      );
    }
  };

  const stop = async () => {
    if (!editing) return;
    done(
      editing.kind === "income"
        ? await incomeStore.endRegular(editing.rule.id, today)
        : editing.kind === "bill"
          ? await incomeStore.endBill(editing.rule.id, today)
          : await bankAccountsStore.endTransfer(editing.rule.id, today),
    );
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[480px]"
      aria-labelledby="rule-title"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <h2 id="rule-title" className="m-0 text-lg font-bold">
            {t("rule.title")}
          </h2>
          {!editing && (
            <Choice<RuleKind>
              label={t("rule.kind")}
              value={kind}
              onChange={setKind}
              options={[
                { value: "income", label: t("rule.income") },
                { value: "bill", label: t("rule.bill") },
                ...(others.length > 0
                  ? [{ value: "transfer" as const, label: t("rule.transfer") }]
                  : []),
              ]}
            />
          )}
          {transfer && (
            <Select
              label={t("rule.to")}
              value={to}
              disabled={editing !== null}
              onChange={(e) => {
                setTo(e.target.value);
              }}
            >
              {others.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          )}
          <Input
            label={t("rule.name")}
            maxLength={80}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label={t("rule.amount", { currency })}
              inputMode="decimal"
              value={amountText}
              onChange={(e) => {
                setAmountText(e.target.value);
              }}
            />
            <Select
              label={t("rule.day")}
              value={day}
              onChange={(e) => {
                setDay(e.target.value);
              }}
            >
              <option value="">{t("rule.anyDay")}</option>
              {DAYS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
              <option value="31">{t("rule.lastDay")}</option>
            </Select>
          </div>
          {kind === "income" && (
            <>
              <Choice<"exact" | "about">
                label={t("rule.kind")}
                value={about ? "about" : "exact"}
                onChange={(value) => {
                  setAbout(value === "about");
                }}
                options={[
                  { value: "exact", label: t("rule.exact") },
                  { value: "about", label: t("rule.about") },
                ]}
              />
              {about && (
                <p className="m-0 text-md leading-relaxed text-muted-foreground">
                  {t("rule.aboutHint")}
                </p>
              )}
            </>
          )}
          {!editing && (
            <p className="m-0 rounded-control bg-muted px-3 py-2.5 text-md">
              {first.nextMonth
                ? t("rule.firstNext", { date: DATE.format(first.date) })
                : t("rule.firstThis", { date: DATE.format(first.date) })}
            </p>
          )}
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-between">
            {editing ? (
              <Button
                type="button"
                variant="danger"
                className="w-full md:w-auto"
                disabled={busy}
                onClick={() => void stop()}
              >
                {t("rule.stop")}
              </Button>
            ) : (
              <span />
            )}
            <div className="flex flex-col-reverse gap-2 md:flex-row">
              <Button
                type="button"
                variant="secondary"
                className="w-full md:w-auto"
                onClick={onClose}
              >
                {t("rule.cancel")}
              </Button>
              <Button type="submit" className="w-full md:w-auto" disabled={!valid || busy}>
                {t("rule.save")}
              </Button>
            </div>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
