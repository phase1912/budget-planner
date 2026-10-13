import { observer } from "mobx-react-lite";
import { Button, IconTile, Modal, ModalBody } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { useTranslation } from "react-i18next";
import { formatAmount } from "@/i18n/format";

/**
 * Confirms erasing a receipt, naming exactly what is about to be lost.
 *
 * Deletion is permanent and takes the photos with it, so the prose states the
 * merchant, the total, the item count and the photo count rather than asking
 * "are you sure?" about an unnamed thing.
 */
export const DeleteReceiptDialog = observer(function DeleteReceiptDialog() {
  const { receiptStore } = useStores();
  const receipt = receiptStore.receiptDetail;
  const { t } = useTranslation("receipts");
  const isOpen = receiptStore.pendingDeleteId !== null;

  if (!isOpen || !receipt) return null;

  const itemCount = receipt.line_items.length;
  const photoCount = receipt.file_ids.length;
  const total = receipt.total_amount ? formatAmount(receipt.total_amount) : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        receiptStore.cancelDelete();
      }}
      className="w-full max-w-[460px]"
      aria-labelledby="delete-receipt-title"
    >
      <ModalBody className="flex flex-col gap-[18px]">
        <div className="flex items-start gap-3.5">
          <IconTile tone="error" size="lg">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 6h18" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
              <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </IconTile>
          <div className="flex flex-col gap-[5px]">
            <h2 id="delete-receipt-title" className="text-[17px] font-bold tracking-[-0.01em]">
              {receipt.merchant_name
                ? t("delete.title", { name: receipt.merchant_name })
                : t("delete.titleUnnamed")}
            </h2>
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              {t(total ? "delete.bodyWorth" : "delete.body", {
                items: t("delete.items", { count: itemCount }),
                photos: t("delete.photos", { count: photoCount }),
                total,
              })}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-[10px]">
          <Button
            variant="ghost"
            onClick={() => {
              receiptStore.cancelDelete();
            }}
          >
            {t("delete.keep")}
          </Button>
          <Button
            variant="danger-solid"
            disabled={receiptStore.isDeleting}
            onClick={() => {
              void receiptStore.deleteReceipt(receipt.id);
            }}
          >
            {receiptStore.isDeleting ? t("delete.deleting") : t("delete.confirm")}
          </Button>
        </div>
      </ModalBody>
    </Modal>
  );
});
