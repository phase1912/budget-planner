import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Select } from "@/shared/components";
import type { BankAccount } from "@/stores/BankAccountsStore";
import { useStores } from "@/stores/StoreContext";
import { WHOLE, rateText, typedAmount } from "../accountFormat";
import { Choice } from "./Choice";

type From = "outside" | "own";

/**
 * Money that reached an account (F23.15, canvas F_Account): from outside — income, of
 * which a business account sets its rate aside, shown with the clean amount at once — or
 * from another of the user's accounts, a transfer that is neither income nor spending.
 */
export const MoneyInDialog = observer(function MoneyInDialog({
  account,
  today,
  onClose,
}: {
  account: BankAccount;
  today: string;
  onClose: () => void;
}) {
  const { bankAccountsStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const currency = authStore.user?.currency ?? "PLN";
  const others = bankAccountsStore.accounts.filter((a) => a.id !== account.id);
  const [from, setFrom] = useState<From>("outside");
  const [fromId, setFromId] = useState(others[0]?.id ?? "");
  const [source, setSource] = useState("");
  const [amountText, setAmountText] = useState("");
  const [day, setDay] = useState(today);
  const amount = typedAmount(amountText);
  const outside = from === "outside";
  const rate = outside ? Number(account.tax_rate ?? 0) : 0;
  const tax = amount === null ? 0 : (Number(amount) * rate) / 100;
  const valid =
    amount !== null && Number(amount) > 0 && (outside ? source.trim() !== "" : fromId !== "");

  const save = async () => {
    if (!valid) return;
    const ok = await bankAccountsStore.moneyIn(
      account.id,
      {
        amount,
        source: outside ? source.trim() : t("in.fromOwn"),
        received_on: day,
        from_account_id: outside ? null : fromId,
      },
      today,
    );
    if (ok) onClose();
  };

  return (
    <Modal isOpen onClose={onClose} className="w-full md:max-w-[460px]" aria-labelledby="in-title">
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <h2 id="in-title" className="m-0 text-lg font-bold">
            {t("in.title")}
          </h2>
          {others.length > 0 && (
            <Choice<From>
              label={t("in.whereFrom")}
              value={from}
              onChange={setFrom}
              options={[
                { value: "outside", label: t("in.fromOutside") },
                { value: "own", label: t("in.fromOwn") },
              ]}
            />
          )}
          {outside ? (
            <Input
              label={t("in.source")}
              placeholder={t("in.sourcePlaceholder")}
              maxLength={80}
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
              }}
            />
          ) : (
            <Select
              label={t("in.from")}
              value={fromId}
              onChange={(e) => {
                setFromId(e.target.value);
              }}
            >
              {others.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          )}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label={t("in.amount", { currency })}
              inputMode="decimal"
              value={amountText}
              onChange={(e) => {
                setAmountText(e.target.value);
              }}
            />
            <Input
              type="date"
              label={t("in.date")}
              value={day}
              max={today}
              onChange={(e) => {
                setDay(e.target.value);
              }}
            />
          </div>
          {amount !== null && (
            <dl className="m-0 flex flex-col gap-1 rounded-control bg-muted px-3 py-2.5 text-md tabular-nums">
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">
                  {rate > 0 ? t("in.tax", { rate: rateText(account.tax_rate) }) : t("in.noTax")}
                </dt>
                <dd className="m-0 font-semibold">
                  {rate > 0 ? `−${WHOLE.format(tax)} ${currency}` : `0 ${currency}`}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="font-bold">{t("in.clean")}</dt>
                <dd className="m-0 font-extrabold">
                  {WHOLE.format(Number(amount) - tax)} {currency}
                </dd>
              </div>
            </dl>
          )}
          <p className="m-0 text-md leading-relaxed text-muted-foreground">
            {outside
              ? account.kind === "business"
                ? t("in.noteBusiness")
                : null
              : t("in.noteTransfer")}
          </p>
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto"
              onClick={onClose}
            >
              {t("account.cancel")}
            </Button>
            <Button
              type="submit"
              className="w-full md:w-auto"
              disabled={!valid || bankAccountsStore.saveState.isLoading}
            >
              {t("account.save")}
            </Button>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
