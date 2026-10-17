import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../Button/Button";
import { Input } from "../Input/Input";
import { Modal, ModalBody } from "../Modal/Modal";

export interface AmountDialogProps {
  title: string;
  label: string;
  hint?: string;
  initial: string;
  currency: string;
  /** Saves the amount (a decimal string with a dot, or "" for none); true closes it. */
  onSave: (amount: string) => Promise<boolean>;
  onClose: () => void;
  /** Whether an empty amount may be saved, meaning "none". */
  allowEmpty?: boolean;
}

/**
 * One amount changed in place (F23.3): this month's income or the monthly budget, from
 * Home, without going to Settings.
 */
export function AmountDialog({
  title,
  label,
  hint,
  initial,
  currency,
  onSave,
  onClose,
  allowEmpty = false,
}: AmountDialogProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const amount = value.trim().replace(",", ".").replace(/\s/g, "");
  const valid =
    (allowEmpty && amount === "") || (/^\d+(\.\d{1,2})?$/.test(amount) && Number(amount) > 0);

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[420px]"
      aria-labelledby="amount-title"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!valid) return;
            setBusy(true);
            void onSave(amount).then((done) => {
              setBusy(false);
              if (done) onClose();
            });
          }}
        >
          <h2 id="amount-title" className="m-0 text-lg font-bold">
            {title}
          </h2>
          <div className="relative flex items-center">
            <Input
              id="amount-value"
              label={label}
              inputMode="decimal"
              autoComplete="off"
              value={value}
              onChange={(event) => {
                setValue(event.target.value);
              }}
              containerClassName="w-full"
              className="w-full pr-14 text-xl font-bold tabular-nums"
            />
            <span className="pointer-events-none absolute right-4 bottom-3 text-lg text-muted-foreground">
              {currency}
            </span>
          </div>
          {hint && <p className="m-0 text-md text-muted-foreground">{hint}</p>}
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto"
              onClick={onClose}
            >
              {t("amountDialog.cancel")}
            </Button>
            <Button type="submit" className="w-full md:w-auto" disabled={!valid || busy}>
              {t("amountDialog.save")}
            </Button>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
}
