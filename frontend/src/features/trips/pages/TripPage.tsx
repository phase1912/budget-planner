import { useEffect, useState } from "react";
import { ArrowLeft, Pencil, Trash2, X } from "lucide-react";
import { observer } from "mobx-react-lite";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { ReceiptDetailModal } from "@/features/receipts/components/ReceiptDetailModal";
import { formatAmount } from "@/i18n/format";
import { formatPurchase } from "@/shared/purchaseDate";
import {
  Button,
  Card,
  ErrorState,
  LoadingState,
  Modal,
  ModalBody,
  ModalFooter,
  Pill,
} from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { TripDialog } from "../components/TripDialog";
import { countryName, formatTripDay } from "../tripFormat";

/**
 * One trip (F20.1): where and when, what it cost — to be reimbursed, for a business
 * trip — and its receipts. A receipt opens to its details and can be taken out of the
 * trip; the trip can be changed or deleted, which gives its receipts back to the month.
 */
export const TripPage = observer(function TripPage() {
  const { id = "" } = useParams();
  const { tripsStore, receiptStore, authStore } = useStores();
  const { t } = useTranslation(["trips", "common", "receipts"]);
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const currency = authStore.user?.currency ?? "PLN";
  const trip = tripsStore.current?.id === id ? tripsStore.current : null;

  useEffect(() => {
    void tripsStore.loadTrip(id);
  }, [tripsStore, id]);

  // A receipt moved or changed from its details changes the trip as well.
  const closedReceipt = receiptStore.selectedReceiptId === null;
  useEffect(() => {
    if (closedReceipt && tripsStore.current?.id === id) void tripsStore.loadTrip(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only on the dialog closing
  }, [closedReceipt]);

  if (!trip) {
    return (
      <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
        <div className="w-full max-w-[1000px]">
          {tripsStore.loadError ? (
            <ErrorState
              title={t("detail.notFound")}
              message={tripsStore.loadError}
              action={<Link to="/trips">{t("detail.back")}</Link>}
            />
          ) : (
            <LoadingState layout="skeleton" />
          )}
        </div>
      </div>
    );
  }

  const place = [trip.city, trip.country ? countryName(trip.country) : null]
    .filter(Boolean)
    .join(", ");

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5">
        <Link
          to="/trips"
          className="inline-flex min-h-11 items-center gap-1.5 self-start text-md font-semibold text-muted-foreground no-underline hover:text-foreground md:min-h-0"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          {t("detail.back")}
        </Link>

        <header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="flex min-w-0 flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="m-0 text-[24px] font-bold tracking-[-0.02em] md:text-[28px]">
                {trip.name}
              </h1>
              <Pill size="sm" tone={trip.kind === "business" ? "info" : "accent"}>
                {t(`kind.${trip.kind}`)}
              </Pill>
            </div>
            <p className="m-0 text-lg text-muted-foreground">
              {t("dates", {
                start: formatTripDay(trip.start_date),
                end: formatTripDay(trip.end_date),
              })}
              {place && ` · ${place}`}
            </p>
            {trip.purpose && <p className="m-0 text-md">{trip.purpose}</p>}
          </div>
          <div className="flex gap-2 [&>*]:flex-1 md:[&>*]:flex-none">
            <Button
              variant="secondary"
              onClick={() => {
                setEditing(true);
              }}
            >
              <Pencil size={14} aria-hidden="true" />
              {t("detail.edit")}
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                setDeleting(true);
              }}
            >
              <Trash2 size={14} aria-hidden="true" />
              {t("detail.delete")}
            </Button>
          </div>
        </header>

        <Card className="flex items-baseline justify-between gap-3 p-4 md:p-5">
          <div className="flex flex-col gap-0.5">
            <span className="text-base text-muted-foreground">
              {t(trip.kind === "business" ? "toReimburse" : "total")}
            </span>
            <span className="text-[24px] font-bold tabular-nums md:text-[28px]">
              {formatAmount(trip.total)} {currency}
            </span>
          </div>
          <span className="text-base text-muted-foreground">
            {t("receipts", { count: trip.receipt_count })}
          </span>
        </Card>

        <section aria-labelledby="trip-receipts" className="flex flex-col gap-2.5">
          <h2 id="trip-receipts" className="m-0 text-lg font-bold">
            {t("detail.receipts")}
          </h2>
          {trip.receipts.length === 0 ? (
            <p className="m-0 text-md text-muted-foreground">{t("detail.noReceipts")}</p>
          ) : (
            <Card flush>
              <ul className="m-0 list-none p-0">
                {trip.receipts.map((receipt) => (
                  <li
                    key={receipt.id}
                    className="flex items-center gap-2 border-b border-border last:border-b-0"
                  >
                    <button
                      type="button"
                      className="flex min-h-14 min-w-0 flex-1 cursor-pointer items-center justify-between gap-3 bg-transparent px-4 py-2.5 text-left hover:bg-surface-hover"
                      onClick={() => void receiptStore.fetchReceiptDetail(receipt.id)}
                    >
                      <span className="flex min-w-0 flex-col">
                        <span className="truncate text-md font-semibold">
                          {receipt.merchant_name ?? t("receipts:list.unknownMerchant")}
                        </span>
                        <span className="flex flex-wrap items-center gap-2 text-base text-muted-foreground">
                          {formatPurchase(receipt.transaction_date ?? receipt.created_at, {
                            day: "numeric",
                            month: "short",
                          })}
                          {receipt.status !== "parsed" && (
                            <Pill size="sm" tone="warning">
                              {t("receipts:status.review")}
                            </Pill>
                          )}
                        </span>
                      </span>
                      <span className="shrink-0 text-md font-semibold tabular-nums">
                        {receipt.total_amount ? formatAmount(receipt.total_amount) : "—"}
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label={t("detail.remove")}
                      title={t("detail.remove")}
                      className="mr-2 inline-flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-control bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                      onClick={() => void tripsStore.placeReceipt(receipt.id, null)}
                    >
                      <X size={16} aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </section>
      </div>

      {receiptStore.selectedReceiptId && <ReceiptDetailModal />}
      {editing && (
        <TripDialog
          tripId={trip.id}
          initial={trip}
          onClose={() => {
            setEditing(false);
          }}
        />
      )}
      {deleting && (
        <Modal
          isOpen
          onClose={() => {
            setDeleting(false);
          }}
          className="md:w-[440px]"
        >
          <ModalBody>
            <p className="m-0 text-md">{t("detail.deleteConfirm", { name: trip.name })}</p>
          </ModalBody>
          <ModalFooter>
            <span className="hidden md:block" />
            <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
              <Button
                variant="ghost"
                onClick={() => {
                  setDeleting(false);
                }}
              >
                {t("common:cancel")}
              </Button>
              <Button
                variant="danger-solid"
                onClick={() => {
                  void tripsStore.remove(trip.id).then((ok) => {
                    if (ok) void navigate("/trips");
                  });
                }}
              >
                {t("detail.delete")}
              </Button>
            </div>
          </ModalFooter>
        </Modal>
      )}
    </div>
  );
});
