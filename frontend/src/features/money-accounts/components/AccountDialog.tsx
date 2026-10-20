import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Switch } from "@/shared/components";
import type { AccountKind, BankAccount } from "@/stores/BankAccountsStore";
import { useStores } from "@/stores/StoreContext";
import { COMMON_RATES, rateText, typedAmount } from "../accountFormat";
import { Choice } from "./Choice";

const KINDS: AccountKind[] = ["personal", "business", "deposit"];

/**
 * Open an account or change one (F23.15, canvas F_Accounts / F_Rules): its name, what it
 * is, what is on it now, the tax a business account sets aside — 5, 6 or 12 %, or the
 * user's own — whether the family shares it and whether purchases are paid from it.
 * An open account can also be brought to what the bank says, or deleted after a
 * confirmation.
 */
export const AccountDialog = observer(function AccountDialog({
  account,
  today,
  onClose,
  onDeleted,
}: {
  account: BankAccount | null;
  today: string;
  onClose: () => void;
  onDeleted?: () => void;
}) {
  const { bankAccountsStore, householdStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const currency = authStore.user?.currency ?? "PLN";
  const stored = rateText(account?.tax_rate);
  const [name, setName] = useState(account?.name ?? "");
  const [kind, setKind] = useState<AccountKind>(account?.kind ?? "personal");
  const [opening, setOpening] = useState(account ? String(Number(account.balance)) : "");
  const [rate, setRate] = useState(
    stored === "" ? "5" : (COMMON_RATES as readonly string[]).includes(stored) ? stored : "own",
  );
  const [ownRate, setOwnRate] = useState(
    (COMMON_RATES as readonly string[]).includes(stored) ? "" : stored,
  );
  const [shared, setShared] = useState(account?.shared ?? householdStore.mayShare);
  const [forPurchases, setForPurchases] = useState(account?.for_purchases ?? false);
  const [correcting, setCorrecting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const busy = bankAccountsStore.saveState.isLoading;
  const amount = opening.trim() === "" ? "0" : typedAmount(opening.replace(/^-/, ""));
  const negative = opening.trim().startsWith("-");
  const taxRate = kind !== "business" ? null : rate === "own" ? typedAmount(ownRate) : rate;
  const valid = name.trim() !== "" && amount !== null && (kind !== "business" || taxRate !== null);

  const save = async () => {
    if (!valid) return;
    const signed = negative ? `-${amount}` : amount;
    // Changing an account keeps where it started; what is on it now is a correction.
    const ok = account
      ? correcting
        ? await bankAccountsStore.adjust(account.id, signed, today)
        : await bankAccountsStore.change(
            account.id,
            {
              name: name.trim(),
              kind,
              opening: account.opening,
              opening_on: account.opening_on,
              tax_rate: taxRate,
              shared,
              for_purchases: forPurchases,
            },
            today,
          )
      : await bankAccountsStore.open(
          {
            name: name.trim(),
            kind,
            opening: signed,
            opening_on: today,
            tax_rate: taxRate,
            shared,
            for_purchases: forPurchases,
          },
          today,
        );
    if (ok) onClose();
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[480px]"
      aria-labelledby="account-title"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <h2 id="account-title" className="m-0 text-lg font-bold">
            {account ? t("account.titleEdit") : t("account.titleNew")}
          </h2>
          {!correcting && (
            <>
              <Input
                label={t("account.name")}
                placeholder={t("account.namePlaceholder")}
                maxLength={60}
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                }}
              />
              {!account && (
                <Choice<AccountKind>
                  label={t("account.kind")}
                  value={kind}
                  onChange={setKind}
                  options={KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) }))}
                />
              )}
            </>
          )}
          {(!account || correcting) && (
            <Input
              label={
                correcting
                  ? t("account.correctLabel", { currency })
                  : t("account.opening", { currency })
              }
              inputMode="decimal"
              value={opening}
              onChange={(e) => {
                setOpening(e.target.value);
              }}
            />
          )}
          {kind === "business" && !correcting && (
            <>
              <Choice
                label={t("account.taxRate")}
                value={rate}
                onChange={setRate}
                options={[
                  ...COMMON_RATES.map((r) => ({ value: r, label: `${r}%` })),
                  { value: "own", label: t("account.own") },
                ]}
              />
              {rate === "own" && (
                <Input
                  label={t("account.ownRate")}
                  inputMode="decimal"
                  value={ownRate}
                  onChange={(e) => {
                    setOwnRate(e.target.value);
                  }}
                />
              )}
              <p className="m-0 text-md leading-relaxed text-muted-foreground">
                {t("account.taxHint")}
              </p>
            </>
          )}
          {!correcting && householdStore.mayShare && (
            <Switch
              checked={shared}
              onChange={setShared}
              label={t("account.shared")}
              ariaLabel={t("account.shared")}
            />
          )}
          {!correcting && kind !== "deposit" && (
            <Switch
              checked={forPurchases}
              onChange={setForPurchases}
              label={t("account.forPurchases")}
              hint={shared ? t("account.forPurchasesShared") : undefined}
              ariaLabel={t("account.forPurchases")}
            />
          )}
          {account && !correcting && (
            <button
              type="button"
              className="min-h-11 self-start text-md font-bold text-primary"
              onClick={() => {
                setOpening(String(Number(account.balance)));
                setCorrecting(true);
              }}
            >
              {t("account.correct")}
            </button>
          )}
          {confirmingDelete && account && (
            <p role="alert" className="m-0 text-md text-foreground">
              {/* The last card takes the user back to a budget alone (F23.21). */}
              {bankAccountsStore.accounts.length === 1
                ? t("account.deleteLast", { name: account.name })
                : t("account.deleteQuestion", { name: account.name })}
            </p>
          )}
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-between">
            {account && !correcting ? (
              <Button
                type="button"
                variant="danger"
                className="w-full md:w-auto"
                disabled={busy}
                onClick={() => {
                  if (!confirmingDelete) {
                    setConfirmingDelete(true);
                    return;
                  }
                  void bankAccountsStore.remove(account.id, today).then((ok) => {
                    if (ok) onDeleted?.();
                  });
                }}
              >
                {t("account.delete")}
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
                {t("account.cancel")}
              </Button>
              <Button type="submit" className="w-full md:w-auto" disabled={!valid || busy}>
                {t("account.save")}
              </Button>
            </div>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
