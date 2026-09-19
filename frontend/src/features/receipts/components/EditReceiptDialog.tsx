import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Button, Input, Modal, ModalBody, ModalFooter, ModalHeader } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { ReceiptDetail } from "@/stores/ReceiptStore";

interface DraftLineItem {
  id: string | null;
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
}

function toDraft(items: ReceiptDetail["line_items"]): DraftLineItem[] {
  return items.map((item) => ({
    id: item.id,
    name: item.name,
    quantity: item.quantity,
    unit_price: item.unit_price,
    total_price: item.total_price,
  }));
}

function sum(items: DraftLineItem[]): number {
  return items.reduce((total, item) => total + (Number(item.total_price) || 0), 0);
}

/**
 * Correct a stored receipt's merchant, date, total and line items (F3.9, BRD A9, A11).
 *
 * Sends the receipt's entire desired state on save, matching what the backend
 * expects: it is not a per-field patch. The backend refuses a total that does
 * not match the line items, the same rule the upload wizard enforces before a
 * receipt is first stored — so a mismatch here surfaces the same way.
 */
export const EditReceiptDialog = observer(function EditReceiptDialog() {
  const { receiptStore } = useStores();
  const receipt = receiptStore.receiptDetail;

  if (!receiptStore.isEditingReceipt || !receipt) return null;

  return <EditReceiptDialogContent key={receipt.id} receipt={receipt} />;
});

const EditReceiptDialogContent = observer(function EditReceiptDialogContent({
  receipt,
}: {
  receipt: ReceiptDetail;
}) {
  const { receiptStore } = useStores();

  const [merchantName, setMerchantName] = useState(receipt.merchant_name ?? "");
  const [transactionDate, setTransactionDate] = useState(
    receipt.transaction_date ? receipt.transaction_date.slice(0, 10) : "",
  );
  const [totalAmount, setTotalAmount] = useState(receipt.total_amount ?? "0");
  const [items, setItems] = useState<DraftLineItem[]>(() => toDraft(receipt.line_items));

  const close = () => {
    receiptStore.cancelEditingReceipt();
  };

  const updateItem = (row: number, field: keyof DraftLineItem, value: string) => {
    setItems((current) =>
      current.map((item, i) => (i === row ? { ...item, [field]: value } : item)),
    );
  };

  const addItem = () => {
    setItems((current) => [
      ...current,
      { id: null, name: "", quantity: "1", unit_price: "0", total_price: "0" },
    ]);
  };

  const removeItem = (row: number) => {
    setItems((current) => current.filter((_, i) => i !== row));
  };

  const computed = sum(items);
  const printed = Number(totalAmount) || 0;
  // A cent of float slop from typed input is not a real mismatch; the backend
  // compares as Decimal and is the actual gate — this is only a preview.
  const matches = Math.abs(computed - printed) < 0.005;

  const save = async () => {
    const ok = await receiptStore.updateReceipt(receipt.id, {
      merchant_name: merchantName || null,
      transaction_date: transactionDate || null,
      total_amount: totalAmount,
      line_items: items.map((item) => ({
        id: item.id,
        name: item.name,
        quantity: item.quantity,
        unit_price: item.unit_price,
        total_price: item.total_price,
      })),
    });
    if (ok) close();
  };

  return (
    <Modal
      isOpen={true}
      onClose={close}
      className="w-full max-w-[720px]"
      aria-labelledby="edit-receipt-title"
    >
      <ModalHeader>
        <h2 id="edit-receipt-title" className="text-lg font-bold tracking-[-0.01em]">
          Edit receipt
        </h2>
      </ModalHeader>

      <ModalBody className="flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Merchant"
            value={merchantName}
            onChange={(e) => {
              setMerchantName(e.target.value);
            }}
          />
          <Input
            label="Date"
            type="date"
            value={transactionDate}
            onChange={(e) => {
              setTransactionDate(e.target.value);
            }}
          />
        </div>

        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-[minmax(0,1fr)_70px_90px_90px_32px] gap-3 text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground">
            <span>Item</span>
            <span className="text-right">Qty</span>
            <span className="text-right">Unit</span>
            <span className="text-right">Total</span>
            <span />
          </div>

          {items.map((item, row) => (
            <div
              key={row}
              className="grid grid-cols-[minmax(0,1fr)_70px_90px_90px_32px] gap-3 items-center"
            >
              <Input
                aria-label={`Name of line ${(row + 1).toString()}`}
                value={item.name}
                onChange={(e) => {
                  updateItem(row, "name", e.target.value);
                }}
              />
              <Input
                aria-label={`Quantity of line ${(row + 1).toString()}`}
                type="number"
                step="0.001"
                className="text-right tabular-nums"
                value={item.quantity}
                onChange={(e) => {
                  updateItem(row, "quantity", e.target.value);
                }}
              />
              <Input
                aria-label={`Unit price of line ${(row + 1).toString()}`}
                type="number"
                step="0.01"
                className="text-right tabular-nums"
                value={item.unit_price}
                onChange={(e) => {
                  updateItem(row, "unit_price", e.target.value);
                }}
              />
              <Input
                aria-label={`Total price of line ${(row + 1).toString()}`}
                type="number"
                step="0.01"
                className="text-right tabular-nums"
                value={item.total_price}
                onChange={(e) => {
                  updateItem(row, "total_price", e.target.value);
                }}
              />
              <button
                type="button"
                aria-label={`Remove line ${(row + 1).toString()}`}
                className="inline-flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:bg-muted hover:text-tone-error-text transition-colors"
                onClick={() => {
                  removeItem(row);
                }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </svg>
              </button>
            </div>
          ))}

          <Button variant="secondary" size="sm" className="self-start" onClick={addItem}>
            Add line
          </Button>
        </div>

        <div className="flex items-center justify-between border-t border-border pt-4">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-medium text-muted-foreground">Total</span>
            <Input
              aria-label="Total amount"
              type="number"
              step="0.01"
              className="w-28 text-right tabular-nums"
              value={totalAmount}
              onChange={(e) => {
                setTotalAmount(e.target.value);
              }}
            />
          </div>
          <span
            className={`text-[13px] font-semibold ${matches ? "text-primary" : "text-tone-error-text"}`}
          >
            {matches
              ? "Lines match the total"
              : `Lines add up to ${computed.toFixed(2)}, not ${printed.toFixed(2)}`}
          </span>
        </div>

        {receiptStore.editReceiptError && (
          <span className="text-[13px] text-tone-error-text">{receiptStore.editReceiptError}</span>
        )}
      </ModalBody>

      <ModalFooter>
        <span className="text-[13px] text-muted-foreground">
          Saving corrects the stored receipt immediately.
        </span>
        <div className="flex items-center gap-[10px]">
          <Button variant="ghost" onClick={close}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={receiptStore.isSavingReceipt}
            onClick={() => {
              void save();
            }}
          >
            {receiptStore.isSavingReceipt ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  );
});
