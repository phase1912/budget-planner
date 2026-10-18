import { useState } from "react";
import { observer } from "mobx-react-lite";
import { FixExtractionDialog } from "./FixExtractionDialog";
import { ResolveTotalForm } from "./ResolveTotalForm";
import { useStores } from "@/stores/StoreContext";
import { alreadyStoredText, type AlreadyStored } from "../alreadyStored";
import { conversionLine, converted } from "@/shared/exchange";
import { Container, Stack } from "@/shared/components/Layout/Layout";
import { Button } from "@/shared/components/Button/Button";
import {
  SecureImage,
  Note,
  Pill,
  TotalsGapNote,
  DoubtfulLinesNote,
  DoubtfulMark,
  CorrectedName,
} from "@/shared/components";
import { dateFormat, formatAmount } from "@/i18n/format";
import { Trans, useTranslation } from "react-i18next";
import i18n from "@/i18n";
import { categoryName } from "@/shared/categoryName";
import { categoryColor } from "@/shared/categoryColor";
import { ArrowRight, Check, ChevronLeft, Layers, Pencil, TriangleAlert } from "lucide-react";
import { TripQuestion } from "@/features/trips/components/TripQuestion";
import { useNavigate } from "react-router-dom";

interface ExtractedLineItem {
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
  confidence?: number;
  /** What was printed, when `name` is the user's remembered correction of it (F15.3). */
  read_name?: string | null;
  /** The reader was unsure of this line — decided by the backend (BRD A10, ADR-0005). */
  is_doubtful?: boolean;
  file_id?: string | null;
  category_id?: string | null;
  category_name?: string | null;
  category_confidence?: number | null;
  /** Set by the backend against the configured threshold — never recomputed here (ADR-0005). */
  category_is_low_confidence?: boolean;
  /** Taken off by an "OPUST" line printed beneath this one, already netted from the total. */
  discount?: string | null;
}

interface ExtractedData {
  merchant_name?: string | null;
  merchant_name_confidence?: number;
  transaction_date?: string | null;
  transaction_date_confidence?: number;
  transaction_time?: string | null;
  transaction_time_confidence?: number;
  receipt_total?: string | null;
  receipt_total_confidence?: number;
  is_receipt_confidence?: number;
  currency?: string;
  items_sum_matches_total?: boolean | null;
  computed_total?: string | null;
  total_reconciled_by?: string | null;
  transaction_date_assumed?: boolean;
  requires_manual_review?: boolean | null;
  line_items?: ExtractedLineItem[];
  file_ids?: string[];
  is_duplicate?: boolean | null;
  duplicate_resolved?: string | null;
  is_skipped?: boolean | null;
  already_stored?: AlreadyStored | null;
  conversion?: Conversion | null;
  position_matches?: {
    item_a_index: number;
    item_b_index: number;
    result: "same" | "different" | "not_possible";
    reason?: string | null;
    user_overridden?: boolean;
  }[];
  error?: string | null;
}

/** The rate a foreign receipt will be stored at, as the server previewed it (F11.7). */
interface Conversion {
  currency: string;
  account_currency: string;
  rate?: string;
  rate_date?: string;
  source?: string;
  unavailable?: boolean;
}

interface ExtractedDataPayload {
  extractions?: ExtractedData[];
}

/**
 * Say exactly what the parser could not read, so the user fixes the right thing.
 *
 * Such a receipt is still stored, flagged for review and left out of the month's
 * budget until it is complete (BRD A11, D3). A missing date is set later from the
 * receipt's Edit dialog, since this step has no date field.
 */
function missingFieldsMessage(data: ExtractedData): string {
  const what =
    !data.receipt_total && !data.transaction_date
      ? i18n.t("upload:read.missingBoth")
      : !data.receipt_total
        ? i18n.t("upload:read.missingTotal")
        : i18n.t("upload:read.missingDate");
  return data.receipt_total ? `${what} ${i18n.t("upload:read.setLater")}` : what;
}

const PURCHASE_DAY = dateFormat({
  day: "numeric",
  month: "long",
  year: "numeric",
});

export const ExtractedStep = observer(function ExtractedStep() {
  const { uploadStore } = useStores();
  const { t } = useTranslation(["upload", "trips"]);
  const navigate = useNavigate();
  const [enteringTotalFor, setEnteringTotalFor] = useState<number | null>(null);
  const [doubtfulOnly, setDoubtfulOnly] = useState<number[]>([]);

  const handleBack = () => {
    uploadStore.resetError();
    uploadStore.resetData();
    uploadStore.uploadState.reset();
  };

  const payload = uploadStore.extractedData as unknown as ExtractedDataPayload | null;
  const extractions = payload?.extractions;

  if (!extractions || extractions.length === 0) return null;

  const totalItems = extractions.reduce((acc, data) => acc + (data.line_items?.length ?? 0), 0);
  const selectable =
    extractions.filter((e) => !e.is_skipped && !e.error && !e.already_stored).length > 1;

  return (
    <Container size="narrow" gutter={false} className="py-4 pb-8 md:py-9">
      <Stack className="gap-4 md:gap-5">
        <div className="flex items-start gap-3">
          <button
            type="button"
            onClick={handleBack}
            aria-label={t("read.back")}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-pill bg-surface text-foreground"
          >
            <ChevronLeft size={20} aria-hidden="true" />
          </button>
          <div className="flex min-w-0 flex-col gap-1">
            <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em]">{t("read.title")}</h1>
            <p className="m-0 text-base text-muted-foreground">
              {t("read.summaryReceipts", { count: uploadStore.lines.length })},{" "}
              {t("read.summaryItems", { count: totalItems })},{" "}
              {t("read.summaryPhotos", { count: uploadStore.totalFilesCount })}.{" "}
              {t("read.notStored")}
            </p>
          </div>
        </div>

        {uploadStore.conflictsCount > 0 && (
          <Note tone="warning">{t("read.conflicts", { count: uploadStore.conflictsCount })}</Note>
        )}

        {extractions.map((data, index) => {
          if (data.is_skipped) return null;
          if (data.already_stored) {
            return (
              <Note key={index} tone="info">
                {alreadyStoredText(data.already_stored, data.merchant_name)}
              </Note>
            );
          }
          const merchantName = data.merchant_name ?? t("read.unknownMerchant");
          const merchantNameLowConf = (data.merchant_name_confidence ?? 100) < 80;
          const transactionDate = data.transaction_date ?? t("read.unknownDate");
          const transactionDateLowConf = (data.transaction_date_confidence ?? 100) < 80;
          const receiptTotalLowConf = (data.receipt_total_confidence ?? 100) < 80;
          const isNotReceipt = (data.is_receipt_confidence ?? 100) < 50;
          const matchesTotal = data.items_sum_matches_total;
          const lineItems = data.line_items ?? [];
          const fileIds = data.file_ids ?? [];

          const duplicateIndices = new Set(
            (data.position_matches ?? [])
              .filter((m) => m.result === "same")
              .map((m) => m.item_b_index),
          );

          const deduplicatedItems = lineItems
            .map((item, idx) => ({ item, idx }))
            .filter(({ idx }) => !duplicateIndices.has(idx));
          const doubtfulItems = deduplicatedItems.filter(({ item }) => item.is_doubtful);
          const showingDoubtful = doubtfulOnly.includes(index) && doubtfulItems.length > 0;
          const shownItems = showingDoubtful ? doubtfulItems : deduplicatedItems;

          if (data.error) {
            return (
              <section
                key={index}
                className="flex items-center gap-3.5 rounded-card bg-tone-error-bg p-4"
              >
                <Thumbs fileIds={fileIds} alt={t("read.thumb")} faded />
                <span className="flex flex-col gap-1">
                  <span className="text-base font-bold text-tone-error-text">
                    {t("read.failedTitle")}
                  </span>
                  <span className="text-md text-tone-error-text opacity-90">
                    {t("read.failedText")}
                  </span>
                </span>
              </section>
            );
          }

          return (
            <section
              key={index}
              aria-label={merchantName}
              className="flex flex-col gap-3 border-t border-border pt-4 first-of-type:border-t-0 first-of-type:pt-0"
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-lg font-extrabold text-primary"
                >
                  {merchantName.charAt(0).toUpperCase()}
                </span>
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span
                    className={`truncate text-lg font-extrabold ${merchantNameLowConf ? "text-tone-warning-text" : ""}`}
                  >
                    {merchantName}
                  </span>
                  <span
                    className={`text-md ${transactionDateLowConf ? "text-tone-warning-text" : "text-muted-foreground"}`}
                  >
                    {transactionDate} &middot;{" "}
                    {t("read.itemsCount", { count: deduplicatedItems.length })} &middot;{" "}
                    {t("read.photos", { count: fileIds.length })}
                  </span>
                </span>
                <button
                  type="button"
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-pill bg-surface text-muted-foreground"
                  aria-label={t("read.edit")}
                  onClick={() => {
                    uploadStore.startEditingExtraction(index);
                  }}
                >
                  <Pencil size={16} aria-hidden="true" />
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Thumbs fileIds={fileIds} alt={t("read.thumb")} />
                {matchesTotal === true && <Pill tone="success">{t("read.totalsMatch")}</Pill>}
                {matchesTotal === null && <Pill tone="warning">{t("read.totalUnsure")}</Pill>}
                {matchesTotal === false && <Pill tone="error">{t("read.totalMismatch")}</Pill>}
              </div>

              {/* Choosing which receipts to store only means something when there are several. */}
              {selectable && (
                <label className="flex min-h-11 cursor-pointer items-center gap-2.5 rounded-control bg-surface px-4 py-2 text-md font-semibold text-foreground">
                  <input
                    type="checkbox"
                    checked={uploadStore.selectedIndices.has(index)}
                    onChange={() => {
                      uploadStore.toggleSelection(index);
                    }}
                    className="h-5 w-5 cursor-pointer rounded border-border accent-primary"
                  />
                  {uploadStore.selectedIndices.has(index) ? t("read.save") : t("read.leaveOut")}
                </label>
              )}

              {uploadStore.selectedIndices.has(index) && <TripQuestion index={index} />}

              {data.transaction_date_assumed && data.transaction_date && (
                <Note tone="info">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <span>
                      <Trans
                        t={t}
                        i18nKey="read.undated"
                        values={{
                          date: PURCHASE_DAY.format(new Date(`${data.transaction_date}T00:00:00`)),
                        }}
                        components={{ b: <strong /> }}
                      />
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="min-h-11 w-full shrink-0 md:min-h-0 md:w-auto"
                      onClick={() => {
                        uploadStore.startEditingExtraction(index);
                      }}
                    >
                      {t("read.changeDate")}
                    </Button>
                  </div>
                </Note>
              )}

              {matchesTotal === false && data.computed_total && data.receipt_total && (
                <TotalsGapNote
                  linesSum={Number(data.computed_total)}
                  printedTotal={Number(data.receipt_total.replace(",", "."))}
                  busy={uploadStore.isAddingDiscount}
                  onAddDiscount={(amount) => void uploadStore.addDiscount(index, amount)}
                  onFix={() => {
                    uploadStore.startEditingExtraction(index);
                  }}
                  triedToFix={data.total_reconciled_by === "unresolved"}
                />
              )}

              {data.conversion && (
                <ConversionNote conversion={data.conversion} total={data.receipt_total} />
              )}

              {isNotReceipt && (
                <Note tone="error" className="items-start">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-bold">{t("read.notReceiptTitle")}</span>
                    <span className="opacity-90">{t("read.notReceiptText")}</span>
                  </div>
                </Note>
              )}

              {data.is_duplicate && (
                <div className="flex flex-col gap-3 rounded-card bg-tone-warning-bg p-4">
                  <div className="flex items-start gap-3">
                    <Layers
                      size={20}
                      aria-hidden="true"
                      className="mt-0.5 shrink-0 text-tone-warning-text"
                    />
                    <div className="flex flex-col gap-1">
                      <span className="text-base font-bold text-tone-warning-text">
                        {t("read.duplicateTitle")}
                      </span>
                      <span className="text-md leading-relaxed text-tone-warning-prose tabular-nums">
                        {t("read.duplicateText", {
                          merchant: merchantName,
                          date: transactionDate,
                          total: data.receipt_total,
                          currency: data.currency ?? "",
                        })}
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <Button
                      variant="secondary"
                      className="min-h-11"
                      onClick={() => {
                        void uploadStore.resolveDuplicate(index, "skip");
                      }}
                    >
                      {t("read.skip")}
                    </Button>
                    <Button
                      variant="primary"
                      className="min-h-11"
                      onClick={() => {
                        void uploadStore.resolveDuplicate(index, "store");
                      }}
                    >
                      {t("read.storeNew")}
                    </Button>
                  </div>
                </div>
              )}

              {data.requires_manual_review && (
                <div className="flex flex-col gap-3 rounded-card bg-tone-error-bg p-4">
                  <div className="flex items-start gap-3">
                    <TriangleAlert
                      size={20}
                      aria-hidden="true"
                      className="mt-0.5 shrink-0 text-tone-error-text"
                    />
                    <div className="flex flex-col gap-1">
                      <span className="text-base font-bold text-tone-error-text">
                        {t("read.needsYou", { merchant: merchantName || t("read.receipt") })}
                      </span>
                      <span className="text-md leading-relaxed text-tone-error-prose">
                        {missingFieldsMessage(data)}
                      </span>
                    </div>
                  </div>
                  {!data.receipt_total &&
                    (enteringTotalFor === index ? (
                      <ResolveTotalForm
                        extractionIndex={index}
                        computedTotal={data.computed_total}
                        lineCount={lineItems.length}
                        autoFocusField
                      />
                    ) : (
                      <Button
                        variant="danger-solid"
                        className="min-h-11 self-stretch md:self-start"
                        onClick={() => {
                          setEnteringTotalFor(index);
                        }}
                      >
                        {t("read.enterTotal")}
                      </Button>
                    ))}
                </div>
              )}

              <DoubtfulLinesNote
                className="rounded-card"
                count={doubtfulItems.length}
                only={showingDoubtful}
                onToggle={() => {
                  setDoubtfulOnly(
                    showingDoubtful
                      ? doubtfulOnly.filter((i) => i !== index)
                      : [...doubtfulOnly, index],
                  );
                }}
                fileIds={fileIds}
                photoAlt={t("read.thumb")}
              />

              <ul className="m-0 flex list-none flex-col overflow-hidden rounded-card bg-surface p-0">
                {shownItems.map(({ item, idx }) => (
                  <LineRow
                    key={idx}
                    item={item}
                    provenance={provenance(data, item, idx)}
                    onUndo={() => void uploadStore.undoCorrection(index, idx, false)}
                    onForget={() => void uploadStore.undoCorrection(index, idx, true)}
                    undoing={uploadStore.isUndoingCorrection}
                  />
                ))}
              </ul>

              <dl className="m-0 flex flex-col gap-2 rounded-card bg-surface p-4">
                <div className="flex justify-between gap-3 text-base">
                  <dt className="text-muted-foreground">{t("read.onReceipt")}</dt>
                  <dd
                    className={`m-0 font-bold tabular-nums ${receiptTotalLowConf ? "text-tone-warning-text" : ""}`}
                  >
                    {data.receipt_total
                      ? `${data.receipt_total} ${data.currency ?? ""}`.trim()
                      : "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 text-base">
                  <dt className="text-muted-foreground">{t("read.linesSum")}</dt>
                  <dd className="m-0 font-bold tabular-nums">
                    {data.computed_total
                      ? `${formatAmount(data.computed_total)} ${data.currency ?? ""}`.trim()
                      : t("read.cannotAddShort")}
                  </dd>
                </div>
                {matchesTotal === true && (
                  <p className="m-0 flex items-center gap-1.5 border-t border-border pt-2 text-md font-semibold text-primary">
                    <Check size={16} aria-hidden="true" />
                    {t("read.matches")}
                  </p>
                )}
                {matchesTotal === false && (
                  <p className="m-0 flex items-center gap-1.5 border-t border-border pt-2 text-md font-semibold text-tone-error-text">
                    <TriangleAlert size={16} aria-hidden="true" />
                    {!data.receipt_total ? t("read.nothingToCheck") : t("read.mismatch")}
                  </p>
                )}
              </dl>
            </section>
          );
        })}

        {uploadStore.unansweredTrips.length > 0 && (
          <Note tone="warning">
            {t("trips:question.unanswered", { count: uploadStore.unansweredTrips.length })}
          </Note>
        )}

        <div className="flex flex-col-reverse gap-2 md:flex-row md:items-center md:justify-between md:gap-4">
          <Button variant="ghost" className="min-h-11" onClick={handleBack}>
            <ChevronLeft size={16} aria-hidden="true" className="mr-1" />
            {t("read.back")}
          </Button>
          {uploadStore.conflictsCount > 0 ? (
            <Button
              variant="primary"
              size="lg"
              className="min-h-14 w-full md:w-auto"
              onClick={() => (uploadStore.currentStep = 3)}
            >
              {t("read.resolve", { count: uploadStore.conflictsCount })}
              <ArrowRight size={18} aria-hidden="true" className="ml-2" />
            </Button>
          ) : (
            <Button
              variant="primary"
              size="lg"
              className="min-h-14 w-full md:w-auto"
              disabled={
                uploadStore.selectedIndices.size === 0 ||
                uploadStore.isCommitting ||
                uploadStore.unansweredTrips.length > 0
              }
              onClick={() => {
                const backTo = uploadStore.fromTrip;
                void uploadStore.commitJob().then((stored) => {
                  if (stored && backTo) void navigate(`/trips/${backTo.id}`);
                });
              }}
            >
              {uploadStore.selectedIndices.size === 0
                ? t("read.nothingToStore")
                : t("read.store", { count: uploadStore.selectedIndices.size })}
            </Button>
          )}
        </div>
      </Stack>

      <FixExtractionDialog />
    </Container>
  );
});

/** Up to two photo thumbnails of a receipt, and how many more there are. */
function Thumbs({
  fileIds,
  alt,
  faded = false,
}: {
  fileIds: string[];
  alt: string;
  faded?: boolean;
}) {
  if (fileIds.length === 0) return null;
  const look = faded ? "opacity-50 grayscale" : "";
  return (
    <span className="flex gap-1.5">
      {fileIds.slice(0, 2).map((id) => (
        <SecureImage
          key={id}
          fileId={id}
          alt={alt}
          className={`h-11 w-9 rounded-md object-cover ${look}`}
        />
      ))}
      {fileIds.length > 2 && (
        <span
          className={`inline-flex h-11 w-9 items-center justify-center rounded-md bg-muted text-xs font-bold text-muted-foreground ${look}`}
        >
          +{fileIds.length - 2}
        </span>
      )}
    </span>
  );
}

/**
 * Which photos of an overlapping set a line was read from ("P1 & P2"), so a line caught in
 * two frames and counted once can be traced (BRD B2-B4). Empty for a single photo.
 */
function provenance(data: ExtractedData, item: ExtractedLineItem, idx: number): string {
  const fileIds = data.file_ids ?? [];
  const lineItems = data.line_items ?? [];
  const fileIndex = item.file_id ? fileIds.indexOf(item.file_id) + 1 : 0;
  if (fileIds.length <= 1 || fileIndex === 0) return "";
  const others = [
    ...new Set(
      (data.position_matches ?? [])
        .filter((m) => m.item_a_index === idx && m.result === "same")
        .map((m) => {
          const other = lineItems[m.item_b_index];
          return other?.file_id ? fileIds.indexOf(other.file_id) + 1 : 0;
        })
        .filter((n) => n > 0 && n !== fileIndex),
    ),
  ];
  const label = `P${fileIndex.toString()}`;
  return others.length > 0 ? `${label} & P${others.join(" & P")}` : label;
}

/**
 * One line as read: its name, the category it will be filed under, and its price — with
 * quantity and any discount beneath. A line the reader was unsure of is drawn in warning.
 */
function LineRow({
  item,
  provenance: from,
  onUndo,
  onForget,
  undoing,
}: {
  item: ExtractedLineItem;
  provenance: string;
  onUndo: () => void;
  onForget: () => void;
  undoing: boolean;
}) {
  const { t } = useTranslation("upload");
  const doubtful = item.is_doubtful === true;
  const category = item.category_name ?? "Uncategorized";
  return (
    <li className="flex items-center gap-3 border-b border-border px-4 py-3 last:border-b-0">
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="flex items-center gap-2 overflow-hidden">
          {from && (
            <span className="inline-flex h-4 shrink-0 items-center justify-center rounded-sm bg-muted px-1.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
              {from}
            </span>
          )}
          <span
            className={`truncate text-base font-bold ${doubtful ? "text-tone-warning-text" : "text-foreground"}`}
          >
            {item.name}
          </span>
          {doubtful && <DoubtfulMark className="shrink-0" />}
        </span>
        {item.read_name && (
          <CorrectedName
            readName={item.read_name}
            busy={undoing}
            onUndo={onUndo}
            onForget={onForget}
          />
        )}
        <span
          className={`flex items-center gap-1.5 text-sm font-semibold ${item.category_is_low_confidence ? "text-tone-warning-text" : "text-muted-foreground"}`}
          title={item.category_is_low_confidence ? t("read.lowConfidence") : undefined}
        >
          <span
            aria-hidden="true"
            className="h-2 w-2 shrink-0 rounded-pill"
            style={{ background: categoryColor(category) }}
          />
          {categoryName(category)}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-0.5 text-right tabular-nums">
        <span
          className={`text-base font-extrabold ${doubtful ? "text-tone-warning-text" : "text-foreground"}`}
        >
          {item.total_price}
        </span>
        <span className="text-sm text-muted-foreground">
          {item.quantity} × {item.unit_price}
        </span>
        {item.discount && (
          <span className="whitespace-nowrap text-sm font-medium text-tone-primary-text">
            {t("read.discount", { amount: item.discount })}
          </span>
        )}
      </span>
    </li>
  );
}

/**
 * What a foreign receipt will count as once stored (F11.7, ADR-0016), following a total
 * corrected in the wizard; or, with no rate to be had, that it will wait in review.
 */
function ConversionNote({ conversion, total }: { conversion: Conversion; total?: string | null }) {
  const { t } = useTranslation("upload");
  const className = "rounded-none border-x-0 border-t-0 px-5 py-3.5";
  if (conversion.unavailable || !conversion.rate) {
    return (
      <Note tone="warning" className={className}>
        {t("conversion.unavailable", {
          currency: conversion.currency,
          account: conversion.account_currency,
        })}
      </Note>
    );
  }
  const amount = converted(total, conversion.rate);
  return (
    <Note tone="info" className={className}>
      {total && amount
        ? conversionLine(total, conversion.currency, amount, conversion.account_currency, {
            rate: conversion.rate,
            rateDate: conversion.rate_date ?? "",
            source: conversion.source ?? "",
          })
        : t("conversion.paidIn", {
            currency: conversion.currency,
            account: conversion.account_currency,
          })}
    </Note>
  );
}
