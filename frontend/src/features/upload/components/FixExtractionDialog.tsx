import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Button, Input, Modal, ModalBody, ModalFooter, ModalHeader } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { useTranslation } from "react-i18next";

interface EditableItem {
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
}

interface ExtractionPayload {
  line_items?: EditableItem[];
  merchant_name?: string | null;
  transaction_date?: string | null;
  transaction_date_assumed?: boolean;
}

/**
 * Lets the user correct what the parser read before any of it is stored: the purchase
 * date (assumed from the upload day when the receipt shows none) and the lines.
 *
 * A receipt whose lines do not add up cannot be committed, so without somewhere
 * to fix a misread price the user would be stuck (BRD A9, A11). Only the rows
 * actually changed are sent, one request each, so an untouched line keeps
 * exactly what the parser produced.
 */
export const FixExtractionDialog = observer(function FixExtractionDialog() {
  const { uploadStore } = useStores();
  const index = uploadStore.editingExtractionIndex;
  const { t } = useTranslation("upload");

  const payload = uploadStore.extractedData as { extractions?: ExtractionPayload[] } | null;
  const extraction = index === null ? undefined : payload?.extractions?.[index];
  const parsedItems = extraction?.line_items ?? [];

  const [draft, setDraft] = useState<EditableItem[] | null>(null);
  const [dateDraft, setDateDraft] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  if (index === null || !extraction) return null;

  const items = draft ?? parsedItems;
  const parsedDate = extraction.transaction_date?.slice(0, 10) ?? "";

  const update = (row: number, field: keyof EditableItem, value: string) => {
    const next = items.map((item, i) => (i === row ? { ...item, [field]: value } : item));
    setDraft(next);
  };

  const close = () => {
    setDraft(null);
    setDateDraft(null);
    uploadStore.stopEditingExtraction();
  };

  const save = async () => {
    setIsSaving(true);
    try {
      if (dateDraft !== null && dateDraft !== "" && dateDraft !== parsedDate) {
        // The store has said why; keep the dialog open so the edit is not lost.
        if (!(await uploadStore.resolveDate(index, dateDraft))) return;
      }
      for (const [row, item] of items.entries()) {
        const original = parsedItems[row];
        if (!original) continue;
        const changed =
          original.name !== item.name ||
          original.quantity !== item.quantity ||
          original.unit_price !== item.unit_price ||
          original.total_price !== item.total_price;
        if (!changed) continue;

        const saved = await uploadStore.updateLineItem(index, row, {
          name: item.name,
          quantity: item.quantity,
          unit_price: item.unit_price,
          total_price: item.total_price,
        });
        // The store has said why; keep the dialog open so the edit is not lost.
        if (!saved) return;
      }
      close();
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={close}
      className="w-full max-w-[760px]"
      aria-labelledby="fix-extraction-title"
    >
      <ModalHeader>
        <div className="flex flex-col gap-1">
          <h2 id="fix-extraction-title" className="text-lg font-bold tracking-[-0.01em]">
            {t("fix.title")}
          </h2>
          <span className="text-[13px] text-muted-foreground">
            {t("fix.subtitle", {
              merchant: extraction.merchant_name ?? t("already.thisReceipt"),
            })}
          </span>
        </div>
      </ModalHeader>

      <ModalBody className="flex flex-col gap-3">
        <div className="flex flex-col gap-1.5 border-b border-border pb-3 md:max-w-60">
          <Input
            id="purchase-date"
            type="date"
            label={t("fix.date")}
            value={dateDraft ?? parsedDate}
            max={new Date().toISOString().slice(0, 10)}
            onChange={(e) => {
              setDateDraft(e.target.value);
            }}
          />
          {extraction.transaction_date_assumed && dateDraft === null && (
            <span className="text-base text-muted-foreground">{t("fix.dateAssumed")}</span>
          )}
        </div>
        <div className="hidden md:grid md:grid-cols-[minmax(0,1fr)_80px_110px_110px] gap-3 text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground">
          <span>{t("cols.item")}</span>
          <span className="text-right">{t("cols.qty")}</span>
          <span className="text-right">{t("cols.unit")}</span>
          <span className="text-right">{t("cols.total")}</span>
        </div>
        {/* A phone lays each line over two rows; this names the amounts in the second. */}
        <div className="grid grid-cols-3 gap-2 text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground md:hidden">
          <span className="text-right">{t("cols.qty")}</span>
          <span className="text-right">{t("cols.unit")}</span>
          <span className="text-right">{t("cols.total")}</span>
        </div>

        {items.map((item, row) => (
          <div
            key={row}
            className="grid grid-cols-3 gap-2 items-center border-b border-border pb-3 md:grid-cols-[minmax(0,1fr)_80px_110px_110px] md:gap-3 md:border-0 md:pb-0"
          >
            <Input
              containerClassName="col-span-3 md:col-span-1"
              aria-label={t("fix.lineName", { n: row + 1 })}
              value={item.name}
              onChange={(e) => {
                update(row, "name", e.target.value);
              }}
            />
            <Input
              aria-label={t("fix.lineQty", { n: row + 1 })}
              className="text-right tabular-nums"
              value={item.quantity}
              onChange={(e) => {
                update(row, "quantity", e.target.value);
              }}
            />
            <Input
              aria-label={t("fix.lineUnit", { n: row + 1 })}
              className="text-right tabular-nums"
              value={item.unit_price}
              onChange={(e) => {
                update(row, "unit_price", e.target.value);
              }}
            />
            <Input
              aria-label={t("fix.lineTotal", { n: row + 1 })}
              className="text-right tabular-nums"
              value={item.total_price}
              onChange={(e) => {
                update(row, "total_price", e.target.value);
              }}
            />
          </div>
        ))}
      </ModalBody>

      <ModalFooter>
        <span className="hidden text-[13px] text-muted-foreground md:inline">
          {t("fix.notStored")}
        </span>
        <div className="flex w-full items-center gap-[10px] md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
          <Button variant="ghost" onClick={close}>
            {t("fix.cancel")}
          </Button>
          <Button
            variant="primary"
            disabled={isSaving}
            onClick={() => {
              void save();
            }}
          >
            {isSaving ? t("fix.saving") : t("fix.save")}
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  );
});
