import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody } from "@/shared/components";
import { formatAmount } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";

/**
 * Paid less than printed (F23.7): the amount not paid, spread over the whole receipt so
 * each category counts what was really paid. "Only on some items" — tucked away, most
 * people never need it — narrows it to the lines ticked. An existing discount can be
 * changed or removed here.
 */
export const DiscountDialog = observer(function DiscountDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const { receiptStore } = useStores();
  const { t } = useTranslation("receipts");
  const receipt = receiptStore.receiptDetail;
  const [value, setValue] = useState(receipt?.paid_discount ?? "");
  const [some, setSome] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);
  if (!receipt) return null;

  const printed = Number(receipt.total_amount ?? 0);
  const amount = value.trim().replace(",", ".").replace(/\s/g, "");
  const scope = some
    ? receipt.line_items.filter((line) => picked.includes(line.id))
    : receipt.line_items;
  const scopeTotal = scope.reduce((sum, line) => sum + Math.max(0, Number(line.total_price)), 0);
  const valid =
    /^\d+(\.\d{1,2})?$/.test(amount) && Number(amount) > 0 && Number(amount) <= scopeTotal;

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[480px]"
      aria-labelledby="discount-title"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!valid) return;
            void receiptStore.setDiscount(amount, some ? picked : null).then((ok) => {
              if (ok) onClose();
            });
          }}
        >
          <h2 id="discount-title" className="m-0 text-lg font-bold">
            {t("discount.title")}
          </h2>
          <p className="m-0 text-md text-muted-foreground">{t("discount.hint")}</p>
          <Input
            id="discount-amount"
            label={t("discount.amount")}
            inputMode="decimal"
            autoComplete="off"
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
            }}
            className="text-xl font-bold tabular-nums"
          />
          <p className="m-0 flex justify-between rounded-control bg-tone-primary-bg px-4 py-3 text-lg font-bold">
            <span>{t("discount.paid")}</span>
            <span className="tabular-nums">
              {formatAmount(Math.max(0, printed - (Number(amount) || 0)).toFixed(2))}
            </span>
          </p>
          {some ? (
            <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
              <legend className="mb-1 text-base text-muted-foreground">
                {t("discount.which")}
              </legend>
              {receipt.line_items.map((line) => (
                <label key={line.id} className="flex min-h-11 items-center gap-3 text-md">
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-primary"
                    checked={picked.includes(line.id)}
                    onChange={(event) => {
                      setPicked((ids) =>
                        event.target.checked
                          ? [...ids, line.id]
                          : ids.filter((id) => id !== line.id),
                      );
                    }}
                  />
                  <span className="flex-1 truncate">{line.name}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {formatAmount(line.total_price)}
                  </span>
                </label>
              ))}
            </fieldset>
          ) : (
            <p className="m-0 text-base text-muted-foreground">{t("discount.whole")}</p>
          )}
          <button
            type="button"
            className="min-h-11 self-start text-md font-semibold text-primary"
            onClick={() => {
              setSome((v) => !v);
            }}
          >
            {some ? t("discount.wholeInstead") : t("discount.some")}
          </button>
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-between">
            {receipt.paid_discount != null ? (
              <Button
                type="button"
                variant="ghost"
                className="w-full md:w-auto"
                disabled={receiptStore.isSavingDiscount}
                onClick={() => {
                  void receiptStore.setDiscount(null).then((ok) => {
                    if (ok) onClose();
                  });
                }}
              >
                {t("discount.remove")}
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
                {t("discount.cancel")}
              </Button>
              <Button
                type="submit"
                className="w-full md:w-auto"
                disabled={!valid || receiptStore.isSavingDiscount}
              >
                {t("discount.apply")}
              </Button>
            </div>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
