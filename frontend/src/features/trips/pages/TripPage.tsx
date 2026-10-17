import { useEffect, useState } from "react";
import { PenLine, Pencil, Plus, Trash2, X } from "lucide-react";
import { observer } from "mobx-react-lite";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { ManualExpenseDialog } from "@/features/receipts/components/ManualExpenseDialog";
import { ReceiptDetailModal } from "@/features/receipts/components/ReceiptDetailModal";
import { formatAmount } from "@/i18n/format";
import { formatPurchase } from "@/shared/purchaseDate";
import {
  BackLink,
  Button,
  Card,
  ErrorState,
  LoadingState,
  Modal,
  ModalBody,
  ModalFooter,
  Pill,
  Select,
} from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { ExpenseKind } from "@/stores/TripsStore";
import { TripDialog } from "../components/TripDialog";
import { PerDiemCard } from "../components/PerDiemCard";
import { SettlementCard } from "../components/SettlementCard";
import { TripAsking } from "../components/TripAsking";
import { TripBudget } from "../components/TripBudget";
import { TripSpending } from "../components/TripSpending";
import { TripStory } from "../components/TripStory";
import { countryName, formatTripDay } from "../tripFormat";

const KINDS: ExpenseKind[] = ["transport", "accommodation", "meals", "other"];

/**
 * One trip (F20.1): where and when, what it cost — to be reimbursed, for a business
 * trip — against its budget and day by day (F20.3), split by kind and currency paid
 * (F20.2), a business trip's per diem (F20.4) and settlement (F20.5), and its receipts. A receipt opens to
 * its details, its kind can be changed in place, and it can be taken out of the trip;
 * the trip can be changed or deleted, which gives its receipts back to the month.
 */
export const TripPage = observer(function TripPage() {
  const { id = "" } = useParams();
  const { tripsStore, receiptStore, authStore } = useStores();
  const { t } = useTranslation(["trips", "common", "receipts"]);
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [addingExpense, setAddingExpense] = useState(false);
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
        {/* Holidays live in Plan; business trips have their own list (F23.12). */}
        <BackLink
          to={trip.kind === "business" ? "/trips?kind=business" : "/plan"}
          label={t("detail.back")}
        />

        <header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="flex min-w-0 flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em]">{trip.name}</h1>
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

        <Card className="flex flex-col gap-3 p-4 md:p-5">
          <div className="flex items-baseline justify-between gap-3">
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
          </div>
          <TripBudget trip={trip} currency={currency} />
        </Card>

        <TripAsking trip={trip} />

        {trip.kind === "business" && <PerDiemCard trip={trip} />}

        {trip.kind === "business" && <SettlementCard trip={trip} />}

        {trip.receipt_count > 0 && <TripSpending trip={trip} currency={currency} />}

        {trip.receipt_count > 0 && <TripStory trip={trip} currency={currency} />}

        <section aria-labelledby="trip-receipts" className="flex flex-col gap-2.5">
          <div className="flex items-center justify-between gap-3">
            <h2 id="trip-receipts" className="m-0 text-lg font-bold">
              {t("detail.receipts")}
            </h2>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                className="min-h-11 md:min-h-0"
                onClick={() => {
                  setAddingExpense(true);
                }}
              >
                <PenLine size={14} aria-hidden="true" />
                {t("receipts:manual.open")}
              </Button>
              <Link to={`/upload?trip=${trip.id}`} className="no-underline">
                <Button size="sm" className="min-h-11 md:min-h-0" tabIndex={-1}>
                  <Plus size={14} aria-hidden="true" />
                  {t("addReceipt")}
                </Button>
              </Link>
            </div>
          </div>
          {trip.receipts.length === 0 ? (
            <p className="m-0 text-md text-muted-foreground">{t("detail.noReceipts")}</p>
          ) : (
            <Card flush>
              <ul className="m-0 list-none p-0">
                {trip.receipts.map((receipt) => (
                  <li
                    key={receipt.id}
                    className="flex flex-wrap items-center gap-x-2 border-b border-border pb-2 last:border-b-0 md:flex-nowrap md:pb-0"
                  >
                    <button
                      type="button"
                      className="flex min-h-14 min-w-0 basis-full cursor-pointer md:flex-1 md:basis-auto items-center justify-between gap-3 bg-transparent px-4 py-2.5 text-left hover:bg-surface-hover"
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
                    <div className="ml-4 min-w-0 flex-1 md:ml-0 md:w-44 md:flex-none">
                      <Select
                        aria-label={t("spending.kindOf", {
                          merchant: receipt.merchant_name ?? t("receipts:list.unknownMerchant"),
                        })}
                        className="w-full"
                        value={receipt.expense_kind}
                        onChange={(e) => {
                          const kind = KINDS.find((k) => k === e.target.value);
                          if (kind) void tripsStore.chooseKind(receipt.id, kind);
                        }}
                      >
                        {KINDS.map((kind) => (
                          <option key={kind} value={kind}>
                            {t(`spending.${kind}`)}
                          </option>
                        ))}
                      </Select>
                    </div>
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
      {addingExpense && (
        <ManualExpenseDialog
          fromTrip={trip}
          onClose={() => {
            setAddingExpense(false);
          }}
          onAdded={() => void tripsStore.loadTrip(trip.id)}
        />
      )}
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
