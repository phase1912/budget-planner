import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody } from "@/shared/components";
import type { AccountEntry } from "@/stores/BankAccountsStore";
import { useStores } from "@/stores/StoreContext";
import { typedAmount } from "../accountFormat";

/**
 * Change one line of this month's history (F23.15, canvas F_Check): an income or a move
 * by its amount and day, or deleted; a rule's occurrence by this month's amount, or
 * skipped — the rule itself stays. Earlier months are closed and never open here.
 */
export const EntryDialog = observer(function EntryDialog({
  entry,
  today,
  onClose,
}: {
  entry: AccountEntry;
  today: string;
  onClose: () => void;
}) {
  const { bankAccountsStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const currency = authStore.user?.currency ?? "PLN";
  const [amountText, setAmountText] = useState(String(Math.abs(Number(entry.amount))));
  const [day, setDay] = useState(entry.day);
  const amount = typedAmount(amountText);
  const fromRule = entry.ref === "bill" || entry.ref === "rule" || entry.ref === "source";
  const valid = amount !== null && Number(amount) > 0;
  const busy = bankAccountsStore.saveState.isLoading;
  const id = entry.ref_id ?? "";

  const finish = (ok: boolean) => {
    if (ok) onClose();
  };
  const save = async () => {
    if (!valid) return;
    if (entry.ref === "income") {
      finish(await bankAccountsStore.changeIncome(id, amount, day, today));
    } else if (entry.ref === "move") {
      finish(await bankAccountsStore.changeMove(id, amount, day, today));
    } else if (entry.ref === "source") {
      finish(await bankAccountsStore.confirm(id, amount, today));
    } else {
      finish(
        await bankAccountsStore.changeOccurrence(
          entry.ref === "bill" ? "bill" : "transfer",
          id,
          amount,
          today,
        ),
      );
    }
  };
  const drop = async () => {
    if (entry.ref === "income") finish(await bankAccountsStore.removeIncome(id, today));
    else if (entry.ref === "move") finish(await bankAccountsStore.deleteMove(id, today));
    else
      finish(
        await bankAccountsStore.changeOccurrence(
          entry.ref === "bill" ? "bill" : "transfer",
          id,
          "0",
          today,
        ),
      );
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[440px]"
      aria-labelledby="entry-title"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <h2 id="entry-title" className="m-0 text-lg font-bold">
            {entry.name || t("change.title")}
          </h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label={t("change.amount", { currency })}
              inputMode="decimal"
              value={amountText}
              onChange={(e) => {
                setAmountText(e.target.value);
              }}
            />
            {!fromRule && (
              <Input
                type="date"
                label={t("change.date")}
                value={day}
                min={`${today.slice(0, 7)}-01`}
                onChange={(e) => {
                  setDay(e.target.value);
                }}
              />
            )}
          </div>
          {fromRule && (
            <p className="m-0 text-md leading-relaxed text-muted-foreground">
              {t("change.ruleNote")}
            </p>
          )}
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-between">
            {entry.ref !== "source" ? (
              <Button
                type="button"
                variant="danger"
                className="w-full md:w-auto"
                disabled={busy}
                onClick={() => void drop()}
              >
                {fromRule ? t("change.skip") : t("change.delete")}
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
                {t("change.cancel")}
              </Button>
              <Button type="submit" className="w-full md:w-auto" disabled={!valid || busy}>
                {t("change.save")}
              </Button>
            </div>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
