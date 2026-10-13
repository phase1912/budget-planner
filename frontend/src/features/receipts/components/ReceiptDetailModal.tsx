import { useState } from "react";
import { observer } from "mobx-react-lite";
import { receiptSource } from "../receiptSource";
import { useStores } from "@/stores/StoreContext";
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Note,
  IconTile,
  SecureImage,
  TotalsGapNote,
} from "@/shared/components";
import { RefreshCw } from "lucide-react";
import { InlineCategoryPicker } from "@/features/categories/components/InlineCategoryPicker";
import { formatPurchase } from "@/shared/purchaseDate";
import { conversionLine } from "@/shared/exchange";
import { useTranslation } from "react-i18next";
import { numberFormat } from "@/i18n/format";
import { categoryName } from "@/shared/categoryName";

/**
 * Render an amount, or an em dash when there is nothing to render.
 *
 * `Number("")` is 0, so formatting a value the parser never read would claim the
 * user spent nothing on that line — the "renders zeros instead of saying there
 * is no data" defect docs/design/README.md calls out.
 */
function formatAmount(value: string | null | undefined, digits = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  const parsed = Number(value);
  return Number.isNaN(parsed)
    ? "—"
    : numberFormat({ minimumFractionDigits: digits, maximumFractionDigits: digits }).format(parsed);
}

export const ReceiptDetailModal = observer(() => {
  const { receiptStore, authStore, householdStore } = useStores();
  const { t } = useTranslation("receipts");
  const receipt = receiptStore.receiptDetail;
  const [showPhotos, setShowPhotos] = useState(false);

  const handleClose = () => {
    receiptStore.clearSelection();
  };

  if (receiptStore.isLoadingDetail) {
    return (
      <Modal isOpen={true} onClose={handleClose} className="md:w-[660px]">
        <div className="p-6 text-center text-muted-foreground">{t("list.loading")}</div>
      </Modal>
    );
  }

  if (!receipt) {
    return null;
  }

  const source = receiptSource(receipt);
  const accountCurrency = authStore.user?.currency ?? "";
  const waitsForRate = Boolean(receipt.original_currency) && !receipt.exchange_rate;
  // Another household member's receipt: theirs to change, ours only to read (ADR-0017).
  const readOnly = receipt.user_id !== authStore.user?.id;
  const addedBy = householdStore.household?.members.find((m) => m.user_id === receipt.user_id);
  const inSharedHousehold = (householdStore.household?.members.length ?? 0) > 1;

  return (
    <Modal isOpen={true} onClose={handleClose} className="md:w-[660px]">
      <ModalHeader>
        <div className="flex items-center gap-[13px]">
          <IconTile tone="success" size="lg">
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
              <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
              <path d="M16 8H8" />
              <path d="M16 12H8" />
              <path d="M13 16H8" />
            </svg>
          </IconTile>
          <div className="flex flex-col gap-[3px]">
            <h2 className="m-0 text-[17px] font-bold md:text-[19px]">
              {receipt.merchant_name ?? t("detail.unknownMerchant")}
            </h2>
            <span className="tabular-nums text-[13px] text-muted-foreground">
              {receipt.transaction_date
                ? formatPurchase(receipt.transaction_date, {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                  }) +
                  " · " +
                  formatPurchase(receipt.transaction_date, { hour: "2-digit", minute: "2-digit" })
                : t("detail.unknownDate")}
              {" · "}
              {source.label}
            </span>
            {source.reference && (
              <span className="break-all text-base text-muted-foreground">
                {t("detail.reference", { reference: source.reference })}
              </span>
            )}
            {readOnly && (
              <span className="text-[13px] text-muted-foreground">
                {t("detail.addedBy", { name: addedBy?.first_name ?? t("detail.anotherMember") })}
              </span>
            )}
            {receipt.original_currency &&
              receipt.original_total &&
              receipt.exchange_rate &&
              receipt.total_amount && (
                <span className="text-[13px] text-muted-foreground">
                  {conversionLine(
                    receipt.original_total,
                    receipt.original_currency,
                    formatAmount(receipt.total_amount),
                    accountCurrency,
                    {
                      rate: receipt.exchange_rate,
                      rateDate: receipt.exchange_rate_date ?? "",
                      source: receipt.exchange_rate_source ?? "",
                    },
                  )}
                </span>
              )}
            {receipt.fiscal_register_id && receipt.fiscal_receipt_number && (
              <span className="break-words text-[13px] text-muted-foreground">
                {t("detail.fiscal", {
                  register: receipt.fiscal_register_id,
                  number: receipt.fiscal_receipt_number,
                })}
              </span>
            )}
          </div>
        </div>
        <button
          className="inline-flex shrink-0 items-center justify-center w-11 h-11 md:w-[34px] md:h-[34px] rounded-chip text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
          onClick={handleClose}
          aria-label={t("detail.close")}
        >
          <svg
            width="18"
            height="18"
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
      </ModalHeader>

      <ModalBody>
        {waitsForRate && !readOnly && (
          <Note tone="warning" className="mb-3">
            {t("detail.noRate", {
              currency: receipt.original_currency,
              account: accountCurrency,
            })}
          </Note>
        )}
        {receipt.possible_duplicate_of_id && !readOnly && (
          <Note tone="warning" className="mb-3">
            <span className="flex flex-col gap-3">
              <span>{t("detail.duplicate")}</span>
              <span className="flex gap-2 [&>*]:flex-1 md:[&>*]:flex-none">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={receiptStore.isKeepingDuplicate}
                  onClick={() => {
                    void receiptStore.keepPossibleDuplicate();
                  }}
                >
                  {t("detail.keepBoth")}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => {
                    receiptStore.confirmDelete(receipt.id);
                  }}
                >
                  <span className="hidden md:inline">{t("detail.removeThis")}</span>
                  <span className="md:hidden">{t("detail.remove")}</span>
                </Button>
              </span>
            </span>
          </Note>
        )}
        {receipt.status === "manual_review" && receipt.total_amount && !readOnly && (
          <TotalsGapNote
            className="mb-3"
            linesSum={receipt.line_items.reduce((sum, item) => sum + Number(item.total_price), 0)}
            printedTotal={Number(receipt.total_amount)}
            onFix={() => {
              receiptStore.startEditingReceipt();
            }}
          />
        )}
        {!readOnly && inSharedHousehold && (
          <div className="mb-3 flex min-h-11 items-start gap-3 rounded-control border border-border p-3">
            <input
              id="receipt-private"
              type="checkbox"
              aria-describedby="receipt-private-hint"
              className="mt-0.5 h-5 w-5 shrink-0 cursor-pointer accent-primary"
              checked={receipt.is_private}
              disabled={receiptStore.isSavingPrivacy}
              onChange={(e) => {
                void receiptStore.setPrivacy(e.target.checked);
              }}
            />
            <div className="flex flex-col gap-0.5">
              <label
                htmlFor="receipt-private"
                className="cursor-pointer text-[13px] font-semibold text-foreground"
              >
                {t("detail.private")}
              </label>
              <span id="receipt-private-hint" className="text-[13px] text-muted-foreground">
                {t("detail.privateHint")}
              </span>
            </div>
          </div>
        )}
        {!readOnly && (
          <div className="flex justify-end pb-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={receiptStore.isRecategorising}
              onClick={() => {
                void receiptStore.recategoriseReceipt();
              }}
            >
              <RefreshCw
                size={14}
                aria-hidden="true"
                className={receiptStore.isRecategorising ? "animate-spin" : ""}
              />
              {t("detail.recategorise")}
            </Button>
          </div>
        )}
        <div className="hidden md:grid md:grid-cols-[minmax(0,1fr)_36px_70px_86px_156px] items-center gap-[12px] pb-1 border-b border-border">
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
            {t("cols.item")}
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
            {t("cols.qty")}
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
            {t("cols.unit")}
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
            {t("cols.total")}
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
            {t("cols.category")}
          </span>
        </div>

        {receipt.line_items.map((item) => (
          <div
            key={item.id}
            className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 gap-y-1.5 py-3 border-b border-border min-h-[44px] last:border-0 md:grid-cols-[minmax(0,1fr)_36px_70px_86px_156px] md:items-center md:gap-[12px] md:py-[11px]"
          >
            <span className="text-[13px] font-medium">{item.name}</span>
            <span className="hidden md:block tabular-nums text-muted-foreground text-right text-[13px]">
              {formatAmount(item.quantity, 0)}
            </span>
            <span className="hidden md:block tabular-nums text-muted-foreground text-right text-[13px]">
              {formatAmount(item.unit_price, 2)}
            </span>
            <span className="tabular-nums text-right text-[14px] font-semibold">
              {formatAmount(item.total_price, 2)}
            </span>
            {/* A phone has no room for the columns: quantity and price go under the name. */}
            <span className="col-span-2 tabular-nums text-[12px] text-muted-foreground md:hidden">
              {formatAmount(item.quantity, 0)} × {formatAmount(item.unit_price, 2)}
            </span>
            <span className="col-span-2 md:col-span-1">
              {readOnly ? (
                <span className="text-[13px] text-muted-foreground">
                  {categoryName(item.category?.name ?? "Uncategorized")}
                </span>
              ) : (
                <InlineCategoryPicker
                  itemId={item.id}
                  itemName={item.name}
                  merchantName={receipt.merchant_name}
                  currentCategoryId={item.category_id}
                  lowConfidence={item.category_is_low_confidence}
                  onCategoryChanged={() => {
                    void receiptStore.reloadReceiptDetail();
                  }}
                />
              )}
            </span>
          </div>
        ))}

        {showPhotos && (
          <div className="flex flex-wrap gap-3 pt-5 mt-5 border-t border-border">
            {receipt.file_ids.length === 0 ? (
              <span className="text-[13px] text-muted-foreground">{t("detail.noPhotos")}</span>
            ) : (
              receipt.file_ids.map((fileId) => (
                <SecureImage
                  key={fileId}
                  fileId={fileId}
                  alt={t("detail.photoAlt", {
                    merchant: receipt.merchant_name ?? t("detail.thisMerchant"),
                  })}
                  className="w-[calc(50%-6px)] h-[176px] object-cover rounded-md border border-border md:w-[132px]"
                />
              ))
            )}
          </div>
        )}
      </ModalBody>

      <ModalFooter>
        <div className="flex items-baseline gap-[10px]">
          <span className="text-[13px] font-medium text-muted-foreground">{t("detail.total")}</span>
          <span className="tabular-nums text-[22px] font-bold tracking-[-0.02em] text-foreground">
            {formatAmount(receipt.total_amount)}
          </span>
        </div>
        {/* Another member's receipt can be read and its photos seen, never changed (F12.4). */}
        <div className="flex w-full items-center gap-[10px] md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
          {!readOnly && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                receiptStore.confirmDelete(receipt.id);
              }}
            >
              <svg
                width="15"
                height="15"
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
              {t("detail.delete")}
            </Button>
          )}
          {/* A receipt read from an email's text has no photos to show (F11.2). */}
          {receipt.file_ids.length > 0 && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setShowPhotos((shown) => !shown);
              }}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-muted-foreground"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="9" cy="9" r="2" />
                <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
              </svg>
              {showPhotos ? (
                t("detail.hidePhotos")
              ) : (
                <>
                  <span className="hidden md:inline">{t("detail.originalPhotos")}</span>
                  <span className="md:hidden">{t("detail.photos")}</span>
                </>
              )}
            </Button>
          )}
          {!readOnly && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                receiptStore.startEditingReceipt();
              }}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
              </svg>
              {t("detail.edit")}
            </Button>
          )}
        </div>
      </ModalFooter>
    </Modal>
  );
});
