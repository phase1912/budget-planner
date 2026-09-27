import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Button, Input, Modal, ModalBody, ModalFooter, ModalHeader } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

interface EditableItem {
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
}

interface ExtractionPayload {
  line_items?: EditableItem[];
  merchant_name?: string | null;
}

/**
 * Lets the user correct what the parser read before any of it is stored.
 *
 * A receipt whose lines do not add up cannot be committed, so without somewhere
 * to fix a misread price the user would be stuck (BRD A9, A11). Only the rows
 * actually changed are sent, one request each, so an untouched line keeps
 * exactly what the parser produced.
 */
export const FixExtractionDialog = observer(function FixExtractionDialog() {
  const { uploadStore } = useStores();
  const index = uploadStore.editingExtractionIndex;

  const payload = uploadStore.extractedData as { extractions?: ExtractionPayload[] } | null;
  const extraction = index === null ? undefined : payload?.extractions?.[index];
  const parsedItems = extraction?.line_items ?? [];

  const [draft, setDraft] = useState<EditableItem[] | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  if (index === null || !extraction) return null;

  const items = draft ?? parsedItems;

  const update = (row: number, field: keyof EditableItem, value: string) => {
    const next = items.map((item, i) => (i === row ? { ...item, [field]: value } : item));
    setDraft(next);
  };

  const close = () => {
    setDraft(null);
    uploadStore.stopEditingExtraction();
  };

  const save = async () => {
    setIsSaving(true);
    try {
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
            Fix what we read
          </h2>
          <span className="text-[13px] text-muted-foreground">
            {extraction.merchant_name ?? "This receipt"} · leave a price empty if the receipt does
            not show one.
          </span>
        </div>
      </ModalHeader>

      <ModalBody className="flex flex-col gap-3">
        <div className="hidden md:grid grid-cols-[minmax(0,1fr)_80px_110px_110px] gap-3 text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground">
          <span>Item</span>
          <span className="text-right">Qty</span>
          <span className="text-right">Unit</span>
          <span className="text-right">Total</span>
        </div>
        {/* A phone lays each line over two rows; this names the amounts in the second. */}
        <div className="grid grid-cols-3 gap-2 text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground md:hidden">
          <span className="text-right">Qty</span>
          <span className="text-right">Unit</span>
          <span className="text-right">Total</span>
        </div>

        {items.map((item, row) => (
          <div
            key={row}
            className="grid grid-cols-3 gap-2 items-center border-b border-border pb-3 md:grid-cols-[minmax(0,1fr)_80px_110px_110px] md:gap-3 md:border-0 md:pb-0"
          >
            <Input
              containerClassName="col-span-3 md:col-span-1"
              aria-label={`Name of line ${(row + 1).toString()}`}
              value={item.name}
              onChange={(e) => {
                update(row, "name", e.target.value);
              }}
            />
            <Input
              aria-label={`Quantity of line ${(row + 1).toString()}`}
              className="text-right tabular-nums"
              value={item.quantity}
              onChange={(e) => {
                update(row, "quantity", e.target.value);
              }}
            />
            <Input
              aria-label={`Unit price of line ${(row + 1).toString()}`}
              className="text-right tabular-nums"
              value={item.unit_price}
              onChange={(e) => {
                update(row, "unit_price", e.target.value);
              }}
            />
            <Input
              aria-label={`Total price of line ${(row + 1).toString()}`}
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
          Nothing is stored until you finish the last step.
        </span>
        <div className="flex w-full items-center gap-[10px] md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
          <Button variant="ghost" onClick={close}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={isSaving}
            onClick={() => {
              void save();
            }}
          >
            {isSaving ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  );
});
