import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Note, Select, Switch } from "@/shared/components";
import { Choice } from "@/features/money-accounts/components/Choice";
import { purchaseCardId } from "@/stores/BankAccountsStore";
import type { IncomeDraft, IncomeEntry, IncomeRequest } from "@/stores/IncomeStore";
import { useStores } from "@/stores/StoreContext";

const KINDS = ["salary", "side", "refund", "other"] as const;
const DAYS = Array.from({ length: 28 }, (_, i) => i + 1);

interface IncomeDialogProps {
  /** The entry to change; none adds a new one dated `defaultDay`. */
  entry: IncomeEntry | null;
  defaultDay: string;
  /** What a document said came in (F23.11): the form starts from it, saved as read. */
  draft?: IncomeDraft | null;
  /** The pending income `draft` came from (F23.11): saving confirms it rather than adding. */
  pendingId?: string;
  onClose: () => void;
  onSaved: () => void;
}

/**
 * One sum that came in, added or changed by hand (F23.10); an existing one can be deleted.
 * Given a `draft` read off a payslip or transfer (F23.11), it opens filled in for the user
 * to check: nothing is saved until they do, and then it is kept as read from a document.
 *
 * With accounts (F23.15) every sum lands on one — the purchase card unless another is
 * picked — and whose it is follows the account. A new one may come every month (a regular
 * income, exact or about) or from another of the user's accounts, which makes it a
 * transfer, never income.
 */
export const IncomeDialog = observer(function IncomeDialog({
  entry,
  defaultDay,
  draft = null,
  pendingId,
  onClose,
  onSaved,
}: IncomeDialogProps) {
  const { incomeStore, authStore, householdStore, bankAccountsStore } = useStores();
  const accounts = bankAccountsStore.accounts;
  const withAccounts = accounts.length > 0;
  const fresh = !entry && !draft && !pendingId;
  const [from, setFrom] = useState<"outside" | "own">("outside");
  const [fromId, setFromId] = useState("");
  const [monthly, setMonthly] = useState(false);
  const [day, setDay] = useState("");
  const [about, setAbout] = useState(false);
  // Inside a household, money that comes in is the family's unless the user says otherwise (F12.8).
  const mayShare = householdStore.mayShare;
  // A child sees the family's money and changes none of it (F12.10).
  const readOnly = householdStore.isChild && entry?.shared === true;
  const paysOwnTaxes = authStore.user?.pays_own_taxes === true;
  const { t } = useTranslation("plan");
  const [form, setForm] = useState<IncomeRequest>({
    received_on: entry?.received_on ?? draft?.received_on ?? defaultDay,
    amount: entry?.amount ?? draft?.amount ?? "",
    source: entry?.source ?? draft?.source ?? t(`income.kinds.${draft?.kind ?? "salary"}`),
    kind: entry?.kind ?? draft?.kind ?? "salary",
    channel: draft ? "document" : undefined,
    taxed: entry?.taxed,
    shared: entry?.shared ?? mayShare,
    // A correction leaves it on the account it reached (F23.15).
    account_id: entry?.account_id ?? purchaseCardId(accounts) ?? null,
  });
  const transfer = fresh && from === "own";
  // Until the user flips it, a new entry is taxed by its kind, as the server decides (F23.16).
  const taxed = form.taxed ?? (form.kind === "salary" || form.kind === "side");
  const amount = String(form.amount).trim().replace(",", ".").replace(/\s/g, "");
  const valid =
    /^\d+(\.\d{1,2})?$/.test(amount) &&
    Number(amount) > 0 &&
    (transfer ? fromId !== "" && fromId !== form.account_id : form.source.trim() !== "");
  const busy = incomeStore.saveState.isLoading || bankAccountsStore.saveState.isLoading;
  const done = (ok: boolean) => {
    if (ok) {
      onSaved();
      onClose();
    }
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[460px]"
      aria-labelledby="income-title"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!valid) return;
            const body = { ...form, amount, source: form.source.trim() };
            const dayNumber = day === "" ? null : Number(day);
            const to = form.account_id ?? "";
            const saved = entry
              ? incomeStore.update(entry.id, body)
              : pendingId
                ? incomeStore.confirmPending(pendingId, body)
                : transfer
                  ? monthly
                    ? bankAccountsStore.addTransfer(
                        { from_account_id: fromId, to_account_id: to, amount, day: dayNumber },
                        defaultDay,
                      )
                    : bankAccountsStore.move(
                        {
                          from_account_id: fromId,
                          to_account_id: to,
                          amount,
                          moved_on: form.received_on,
                        },
                        defaultDay,
                      )
                  : monthly
                    ? incomeStore.addRegular(
                        {
                          name: body.source,
                          amount,
                          day: dayNumber,
                          taxed,
                          shared: body.shared,
                          account_id: body.account_id,
                          about,
                        },
                        defaultDay,
                      )
                    : incomeStore.add(body);
            void saved.then(done);
          }}
        >
          <h2 id="income-title" className="m-0 text-lg font-bold">
            {entry ? t("income.edit") : draft ? t("income.fromDocument") : t("income.add")}
          </h2>
          {draft && (
            <p className="m-0 text-md text-muted-foreground">{t("income.fromDocumentHint")}</p>
          )}
          {/* Read off a document, it is the user's call whether their tax comes out of it. */}
          {draft && paysOwnTaxes && (
            <p className="m-0 rounded-control bg-tone-warning-bg px-3 py-2 text-md text-tone-warning-text">
              {t("income.decideTax")}
            </p>
          )}
          {withAccounts && (
            <Select
              id="income-account"
              label={t("income.account")}
              value={form.account_id ?? ""}
              onChange={(e) => {
                setForm((f) => ({ ...f, account_id: e.target.value }));
              }}
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          )}
          {!withAccounts && (
            <p className="m-0 text-md text-muted-foreground">{t("income.cardOpens")}</p>
          )}
          {fresh && withAccounts && accounts.length > 1 && (
            <Choice<"outside" | "own">
              label={t("income.whereFrom")}
              value={from}
              onChange={setFrom}
              options={[
                { value: "outside", label: t("income.fromOutside") },
                { value: "own", label: t("income.fromOwn") },
              ]}
            />
          )}
          {transfer && (
            <Select
              id="income-from"
              label={t("income.fromAccount")}
              value={fromId}
              onChange={(e) => {
                setFromId(e.target.value);
              }}
            >
              <option value="" disabled>
                —
              </option>
              {accounts
                .filter((a) => a.id !== form.account_id)
                .map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
            </Select>
          )}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              id="income-amount"
              label={t("income.amount")}
              inputMode="decimal"
              value={form.amount}
              onChange={(e) => {
                setForm((f) => ({ ...f, amount: e.target.value }));
              }}
              required
            />
            {monthly ? (
              <Select
                id="income-day"
                label={t("income.day")}
                value={day}
                onChange={(e) => {
                  setDay(e.target.value);
                }}
              >
                <option value="">{t("income.anyDay")}</option>
                {DAYS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
                <option value="31">{t("income.lastDay")}</option>
              </Select>
            ) : (
              <Input
                id="income-date"
                type="date"
                label={t("income.date")}
                value={form.received_on}
                onChange={(e) => {
                  setForm((f) => ({ ...f, received_on: e.target.value }));
                }}
                required
              />
            )}
            {!transfer && (
              <Input
                id="income-source"
                label={t("income.source")}
                placeholder={t("income.sourcePlaceholder")}
                maxLength={80}
                value={form.source}
                onChange={(e) => {
                  setForm((f) => ({ ...f, source: e.target.value }));
                }}
                required
              />
            )}
            {!transfer && !monthly && (
              <Select
                id="income-kind"
                label={t("income.kind")}
                value={form.kind}
                onChange={(e) => {
                  setForm((f) => ({ ...f, kind: e.target.value as IncomeRequest["kind"] }));
                }}
              >
                {KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {t(`income.kinds.${kind}`)}
                  </option>
                ))}
              </Select>
            )}
          </div>
          {fresh && (
            <Switch
              checked={monthly}
              onChange={setMonthly}
              label={t("income.monthly")}
              ariaLabel={t("income.monthly")}
            />
          )}
          {monthly && !transfer && (
            <Choice<"exact" | "about">
              label={t("income.howMuch")}
              value={about ? "about" : "exact"}
              onChange={(value) => {
                setAbout(value === "about");
              }}
              options={[
                { value: "exact", label: t("income.exact") },
                { value: "about", label: t("income.about") },
              ]}
            />
          )}
          {transfer && (
            <p className="m-0 text-md text-muted-foreground">{t("income.transferHint")}</p>
          )}
          {/* An account with its own rate sets tax aside by it (F23.15); on any other the
              user's own rule does, and this says whether it applies. */}
          {paysOwnTaxes &&
            !transfer &&
            !bankAccountsStore.byId(form.account_id ?? "")?.tax_rate && (
              <Switch
                checked={taxed}
                onChange={(value) => {
                  setForm((f) => ({ ...f, taxed: value }));
                }}
                label={t("income.taxed")}
                ariaLabel={t("income.taxed")}
              />
            )}
          {readOnly && <Note tone="info">{t("income.childReadOnly")}</Note>}
          {mayShare && !withAccounts && (
            <Switch
              checked={form.shared}
              onChange={(value) => {
                setForm((f) => ({ ...f, shared: value }));
              }}
              label={t("income.shared")}
              ariaLabel={t("income.shared")}
            />
          )}
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-between">
            {entry && !readOnly ? (
              <Button
                type="button"
                variant="danger"
                className="w-full md:w-auto"
                disabled={busy}
                onClick={() => {
                  void incomeStore.remove(entry.id).then(done);
                }}
              >
                {t("income.delete")}
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
                {t("income.cancel")}
              </Button>
              {!readOnly && (
                <Button type="submit" className="w-full md:w-auto" disabled={!valid || busy}>
                  {t("income.save")}
                </Button>
              )}
            </div>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
