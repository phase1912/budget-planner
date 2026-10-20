import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Select } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { typedAmount } from "../accountFormat";

/**
 * Move money between two of the accounts the user sees (F23.15, canvas F_Accounts): a
 * transfer, neither income nor spending — only the two balances change.
 */
export const MoveDialog = observer(function MoveDialog({
  fromId,
  today,
  onClose,
}: {
  fromId?: string;
  today: string;
  onClose: () => void;
}) {
  const { bankAccountsStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const currency = authStore.user?.currency ?? "PLN";
  const accounts = bankAccountsStore.accounts;
  const [from, setFrom] = useState(fromId ?? accounts[0]?.id ?? "");
  const [to, setTo] = useState(
    accounts.find((a) => a.id !== (fromId ?? accounts[0]?.id))?.id ?? "",
  );
  const [amountText, setAmountText] = useState("");
  const [day, setDay] = useState(today);
  const amount = typedAmount(amountText);
  const valid = amount !== null && Number(amount) > 0 && from !== "" && to !== "" && from !== to;

  const save = async () => {
    if (!valid) return;
    const ok = await bankAccountsStore.move(
      { from_account_id: from, to_account_id: to, amount, moved_on: day },
      today,
    );
    if (ok) onClose();
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[460px]"
      aria-labelledby="move-title"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <h2 id="move-title" className="m-0 text-lg font-bold">
            {t("moveDialog.title")}
          </h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Select
              label={t("moveDialog.from")}
              value={from}
              onChange={(e) => {
                setFrom(e.target.value);
              }}
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
            <Select
              label={t("moveDialog.to")}
              value={to}
              onChange={(e) => {
                setTo(e.target.value);
              }}
            >
              {accounts
                .filter((a) => a.id !== from)
                .map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
            </Select>
            <Input
              label={t("moveDialog.amount", { currency })}
              inputMode="decimal"
              value={amountText}
              onChange={(e) => {
                setAmountText(e.target.value);
              }}
            />
            <Input
              type="date"
              label={t("moveDialog.date")}
              value={day}
              min={`${today.slice(0, 7)}-01`}
              onChange={(e) => {
                setDay(e.target.value);
              }}
            />
          </div>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">
            {t("moveDialog.hint")}
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
              {t("moveDialog.submit")}
            </Button>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
