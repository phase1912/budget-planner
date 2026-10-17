import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Select } from "@/shared/components";
import type { IncomeEntry, IncomeRequest } from "@/stores/IncomeStore";
import { useStores } from "@/stores/StoreContext";

const KINDS = ["salary", "side", "refund", "other"] as const;

interface IncomeDialogProps {
  /** The entry to change; none adds a new one dated `defaultDay`. */
  entry: IncomeEntry | null;
  defaultDay: string;
  onClose: () => void;
  onSaved: () => void;
}

/** One sum that came in, added or changed by hand (F23.10); an existing one can be deleted. */
export const IncomeDialog = observer(function IncomeDialog({
  entry,
  defaultDay,
  onClose,
  onSaved,
}: IncomeDialogProps) {
  const { incomeStore } = useStores();
  const { t } = useTranslation("plan");
  const [form, setForm] = useState<IncomeRequest>({
    received_on: entry?.received_on ?? defaultDay,
    amount: entry?.amount ?? "",
    source: entry?.source ?? t("income.kinds.salary"),
    kind: entry?.kind ?? "salary",
  });
  const amount = String(form.amount).trim().replace(",", ".").replace(/\s/g, "");
  const valid = /^\d+(\.\d{1,2})?$/.test(amount) && Number(amount) > 0 && form.source.trim() !== "";
  const busy = incomeStore.saveState.isLoading;
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
            void (entry ? incomeStore.update(entry.id, body) : incomeStore.add(body)).then(done);
          }}
        >
          <h2 id="income-title" className="m-0 text-lg font-bold">
            {entry ? t("income.edit") : t("income.add")}
          </h2>
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
          </div>
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-between">
            {entry ? (
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
              <Button type="submit" className="w-full md:w-auto" disabled={!valid || busy}>
                {t("income.save")}
              </Button>
            </div>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
