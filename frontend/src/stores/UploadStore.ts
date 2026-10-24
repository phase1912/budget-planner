import { makeAutoObservable, runInAction } from "mobx";
import type { ToastStore } from "./ToastStore";
import { errorMessage } from "../api/errors";
import type { ApiClient } from "@/api/client";
import { AsyncState } from "@/stores/AsyncState";
import i18n from "@/i18n";
import { device } from "@/platform";
import type { Trip } from "@/stores/TripsStore";
import { tripOnDay } from "@/stores/tripOnDay";
import { shrinkPhoto } from "@/stores/shrinkPhoto";
import { isoDay } from "@/stores/StatisticsStore";
import { dateFormat } from "@/i18n/format";

/** Failed polls in a row (about 2 s apart, plus each request's own wait) before giving up. */
const POLL_FAILURES_TOLERATED = 6;

/**
 * Whether a receipt's printed total still needs the user (BRD A11): none was
 * read, or it was read with low confidence. One decision either way, so the
 * "N things" counter and the cards on both wizard steps agree.
 */
export function totalNeedsDecision(extraction: {
  receipt_total?: unknown;
  receipt_total_confidence?: unknown;
}): boolean {
  if (!extraction.receipt_total) return true;
  return (
    typeof extraction.receipt_total_confidence === "number" &&
    extraction.receipt_total_confidence < 80
  );
}

export class UploadStore {
  readonly uploadState = new AsyncState();
  errorDetails: string | null = null;
  fileIds: string[] = [];
  jobId: string | null = null;
  isProcessing = false;
  /** Shared receipts waiting for the one under review to be finished (F25.2.2). */
  sharedWaiting: File[] = [];
  errorTitle: string | null = null;
  /** The refusal's code, when the server gave one — the screen offers its own way out. */
  errorCode: string | null = null;
  api: ApiClient;
  extractedData: Record<string, unknown> | null = null;
  totalItems = 0;
  processedItems = 0;
  selectedIndices = new Set<number>();
  editingExtractionIndex: number | null = null;

  mode: "single" | "multiple" = "single";
  lines: File[][] = [[]];
  currentStep: 1 | 2 | 3 = 1;

  isCommitting = false;
  /** A missed discount is being added; holds the button so one click adds one. */
  isAddingDiscount = false;
  isUndoingCorrection = false;
  /** The trip whose page the upload started from: its receipts go there, unasked (F20.1). */
  fromTrip: Trip | null = null;
  /** The user's answer per receipt dated within a trip: that trip's id, or null for none. */
  tripAnswers = new Map<number, string | null>();
  private trips: () => Trip[] = () => [];
  private readonly toastStore: ToastStore | undefined;
  private readonly onReceiptsStored: () => void;
  private readonly onUploadSent: () => void;

  /**
   * `onReceiptsStored` runs once receipts are committed, so the month figure can refetch
   * (D6); `onUploadSent` once an upload is answered, so the receipt quota can (F10.6).
   */
  constructor(
    api: ApiClient,
    toastStore?: ToastStore,
    onReceiptsStored: () => void = () => undefined,
    onUploadSent: () => void = () => undefined,
  ) {
    this.api = api;
    this.toastStore = toastStore;
    this.onReceiptsStored = onReceiptsStored;
    this.onUploadSent = onUploadSent;
    makeAutoObservable<this, "onReceiptsStored" | "onUploadSent" | "trips">(this, {
      onReceiptsStored: false,
      onUploadSent: false,
      trips: false,
    });
  }

  /** Where the user's trips are read from, to ask about receipts dated within one. */
  useTrips(trips: () => Trip[]) {
    this.trips = trips;
  }

  /** Start the upload from a trip's page, or (null) from anywhere else. */
  setFromTrip(trip: Trip | null) {
    this.fromTrip = trip;
    this.tripAnswers.clear();
  }

  /**
   * The trip a read receipt's date falls within, which the wizard asks about (F20.1).
   * None when the upload started from a trip's page: that trip is the answer.
   */
  tripFor(index: number): Trip | null {
    if (this.fromTrip) return null;
    const extractions = (this.extractedData?.extractions ?? []) as Record<string, unknown>[];
    const day = extractions[index]?.transaction_date;
    if (typeof day !== "string") return null;
    return tripOnDay(this.trips(), day);
  }

  /**
   * Whether a receipt is going into the trip its date falls within. A personal trip
   * takes it unless the user unticks it; a business trip only once the user says so,
   * and until then there is no answer (undefined).
   */
  goesIntoTrip(index: number): boolean | undefined {
    const trip = this.tripFor(index);
    if (!trip) return undefined;
    const answer = this.tripAnswers.get(index);
    if (answer !== undefined) return answer === trip.id;
    return trip.kind === "personal" ? true : undefined;
  }

  answerTrip(index: number, intoTrip: boolean) {
    const trip = this.tripFor(index);
    if (trip) this.tripAnswers.set(index, intoTrip ? trip.id : null);
  }

  /** Selected receipts a business trip still asks about; storing waits for every answer. */
  get unansweredTrips(): number[] {
    return Array.from(this.selectedIndices).filter(
      (i) => this.tripFor(i)?.kind === "business" && this.goesIntoTrip(i) === undefined,
    );
  }

  private get tripChoices(): { index: number; trip_id: string | null }[] {
    return Array.from(this.selectedIndices).flatMap((index) => {
      if (this.fromTrip) return [{ index, trip_id: this.fromTrip.id }];
      const answer = this.tripAnswers.get(index);
      return answer === undefined ? [] : [{ index, trip_id: answer }];
    });
  }

  /**
   * Tell the user a wizard action failed, and report whether it succeeded.
   *
   * Every action here is fired from a click handler that cannot await it, so
   * an error thrown back to the caller vanished unseen; it is shown here instead.
   */
  private report(error: unknown, fallback: string): false {
    console.error(error);
    this.toastStore?.showError(error instanceof Error ? error.message : fallback);
    return false;
  }

  startEditingExtraction(index: number) {
    this.editingExtractionIndex = index;
  }

  stopEditingExtraction() {
    this.editingExtractionIndex = null;
  }

  toggleSelection(index: number) {
    if (this.selectedIndices.has(index)) {
      this.selectedIndices.delete(index);
    } else {
      this.selectedIndices.add(index);
    }
  }

  setMode(mode: "single" | "multiple") {
    this.mode = mode;
    // reset lines if needed
    if (mode === "single") {
      this.lines = [this.lines[0] ?? []];
    } else {
      if (this.lines.length === 0) {
        this.lines = [[]];
      }
    }
  }

  get files() {
    return this.lines[0] ?? [];
  }

  /**
   * Receipts shared from another app (F25.2.2) become the photos of the next receipt: at
   * once on the first step, or once the receipt being reviewed now is done with — never
   * mixed into it.
   */
  receiveShared(files: File[]) {
    if (this.currentStep === 1 && !this.isProcessing) this.addFilesToLine(0, files);
    else this.sharedWaiting = [...this.sharedWaiting, ...files];
  }

  // legacy method for single mode
  addFiles(newFiles: File[]) {
    this.addFilesToLine(0, newFiles);
  }

  // legacy method for single mode
  removeFile(index: number) {
    this.removeFileFromLine(0, index);
  }

  addFilesToLine(lineIndex: number, newFiles: File[]) {
    this.lines[lineIndex] ??= [];
    this.lines[lineIndex] = [...this.lines[lineIndex], ...newFiles];
  }

  removeFileFromLine(lineIndex: number, fileIndex: number) {
    if (this.lines[lineIndex]) {
      this.lines[lineIndex].splice(fileIndex, 1);
    }
  }

  addLine() {
    this.lines.push([]);
  }

  removeLine(lineIndex: number) {
    this.lines.splice(lineIndex, 1);
  }

  get totalSize() {
    return this.files.reduce((acc, file) => acc + file.size, 0);
  }

  get totalSizeMB() {
    return (this.totalSize / (1024 * 1024)).toFixed(1);
  }

  get isOverLimit() {
    return this.files.length > 10 || this.totalSize > 50 * 1024 * 1024;
  }

  getLineTotalSize(lineIndex: number) {
    const line = this.lines[lineIndex] ?? [];
    return line.reduce((acc, file) => acc + file.size, 0);
  }

  getLineTotalSizeMB(lineIndex: number) {
    return (this.getLineTotalSize(lineIndex) / (1024 * 1024)).toFixed(1);
  }

  isLineOverLimit(lineIndex: number) {
    const line = this.lines[lineIndex] ?? [];
    return line.length > 10 || this.getLineTotalSize(lineIndex) > 50 * 1024 * 1024;
  }

  get isAnyLineOverLimit() {
    return this.lines.some((_, i) => this.isLineOverLimit(i));
  }

  get totalFilesCount() {
    return this.lines.reduce((acc, line) => acc + line.length, 0);
  }

  get allLinesTotalSizeMB() {
    const size = this.lines.reduce((acc, _, i) => acc + this.getLineTotalSize(i), 0);
    return (size / (1024 * 1024)).toFixed(1);
  }

  async submitUpload(): Promise<boolean> {
    if (this.totalFilesCount === 0) return false;

    this.uploadState.start();
    this.errorDetails = null;
    this.errorTitle = null;
    this.errorCode = null;
    this.jobId = null;
    this.isProcessing = false;
    this.extractedData = null;
    this.totalItems = 0;
    this.processedItems = 0;
    this.selectedIndices.clear();

    try {
      const formData = new FormData();

      let error: unknown;
      let response: { status: number } = { status: 200 };
      let data: { job_id?: string } | undefined;

      if (this.mode === "single") {
        for (const file of await Promise.all(this.files.map(shrinkPhoto))) {
          formData.append("files", file);
        }
        const res = await this.api.POST("/receipts/upload", {
          // @ts-expect-error openapi-fetch types do not correctly handle FormData
          body: formData,
        });
        error = res.error;
        response = res.response;
        data = res.data;
      } else {
        const shrunk = await Promise.all(
          this.lines.map((line) => Promise.all(line.map(shrinkPhoto))),
        );
        shrunk.forEach((line, index) => {
          for (const file of line) {
            formData.append(`line_${String(index)}`, file);
          }
        });
        const res = await this.api.POST("/receipts/upload/batch", {
          // @ts-expect-error openapi-fetch types do not correctly handle FormData
          body: formData,
        });
        error = res.error;
        response = res.response;
        data = res.data;
      }

      const startedJobId = runInAction(() => {
        if (error) {
          const { title, code } = error as { title?: string; code?: string };
          this.uploadState.fail(errorMessage(error, i18n.t("messages:upload.failed")));
          this.errorCode = code ?? null;

          // A refusal the server explains — an unsupported file, a limit, the AI not yet
          // allowed — is shown with its reason in the user's language (F24.3); anything else
          // gets the generic message. The server's title is English, so another language
          // keeps the product's own heading.
          const coded = code !== undefined && code !== "internal_error";
          const explained =
            coded || ([400, 403, 415, 429, 503].includes(response.status) && Boolean(title));
          if (explained) {
            this.errorTitle =
              i18n.language === "en" && title ? title : i18n.t("messages:upload.errorTitle");
            this.errorDetails = errorMessage(error, i18n.t("messages:unknown"));
          } else {
            this.errorTitle = i18n.t("messages:upload.errorTitle");
            this.errorDetails = i18n.t("messages:upload.errorDetails");
          }
          return null;
        } else {
          if (data?.job_id) {
            this.jobId = data.job_id;
            this.isProcessing = true;
            return data.job_id;
          }
          return null;
        }
      });

      this.onUploadSent();
      if (startedJobId) {
        void this.pollJobStatus(startedJobId);
      }
      return startedJobId !== null;
    } catch {
      runInAction(() => {
        this.uploadState.fail(i18n.t("messages:upload.network"));
        this.errorTitle = i18n.t("messages:upload.networkTitle");
        this.errorDetails = i18n.t("messages:upload.networkDetails");
      });
      return false;
    }
  }

  /**
   * Follow a reading job until it is done. The job runs on the server whatever happens
   * here, so a poll that fails — a busy instance, a dropped connection, a phone waking —
   * is tried again; only several failures in a row, or a job the server no longer has,
   * end it as an error.
   */
  async pollJobStatus(jobId: string) {
    let polling = true;
    let failures = 0;
    const giveUp = () => {
      runInAction(() => {
        this.isProcessing = false;
        this.uploadState.fail(i18n.t("messages:upload.pollingFailed"));
        this.errorTitle = i18n.t("messages:upload.networkTitle");
        this.errorDetails = i18n.t("messages:upload.pollingDetails");
      });
    };
    while (polling) {
      try {
        const res = await this.api.GET("/receipts/upload/{job_id}", {
          params: { path: { job_id: jobId } },
        });
        if (res.data) failures = 0;

        if (res.data) {
          runInAction(() => {
            this.totalItems = res.data.total_items;
            this.processedItems = res.data.processed_items;

            if (res.data.status === "completed") {
              void device.feel("read");
              this.isProcessing = false;
              this.uploadState.succeed();
              this.fileIds = res.data.file_ids;
              this.extractedData = res.data.extracted_data ?? null;

              this.selectedIndices.clear();
              // A receipt the user already has is never stored again (F11.5).
              if (this.extractedData?.extractions) {
                const extractions = this.extractedData.extractions as Record<string, unknown>[];
                extractions.forEach((ext, idx) => {
                  if (!ext.error && !ext.already_stored) {
                    this.selectedIndices.add(idx);
                  }
                });
              }

              this.currentStep = 2;
              polling = false;
            } else if (res.data.status === "failed") {
              this.isProcessing = false;
              this.uploadState.fail(i18n.t("messages:upload.processingFailed"));
              this.errorTitle = i18n.t("messages:upload.processingTitle");
              this.errorDetails = i18n.t("messages:upload.processingDetails");
              polling = false;
            }
          });
        } else if (res.response.status === 404 || ++failures >= POLL_FAILURES_TOLERATED) {
          giveUp();
          polling = false;
        }
      } catch (err) {
        console.error("Polling error", err);
        if (++failures >= POLL_FAILURES_TOLERATED) {
          giveUp();
          polling = false;
        }
      }

      if (polling) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }
  }

  resetError() {
    this.errorTitle = null;
    this.errorDetails = null;
    this.uploadState.reset();
  }

  resetData() {
    this.extractedData = null;
    this.fileIds = [];
    this.totalItems = 0;
    this.processedItems = 0;
    this.selectedIndices.clear();
    this.tripAnswers.clear();
    this.currentStep = 1;
  }

  /**
   * Back to an empty first step, ready for the next receipt.
   *
   * Unlike `resetData`, which "Back to photos" uses to keep the chosen photos for
   * another try, this also forgets the photos, the mode and the job: they belong
   * to receipts that are now stored.
   */
  startOver() {
    this.resetData();
    this.resetError();
    this.lines = [this.sharedWaiting];
    this.sharedWaiting = [];
    this.mode = "single";
    this.jobId = null;
    this.isProcessing = false;
    this.editingExtractionIndex = null;
  }

  /** How many receipts a commit of the current selection would store; skipped duplicates don't count. */
  get receiptsToStore(): number {
    const extractions = (this.extractedData?.extractions ?? []) as Record<string, unknown>[];
    return Array.from(this.selectedIndices).filter((i) => {
      const extraction = extractions[i];
      return extraction && !extraction.is_skipped && extraction.duplicate_resolved !== "skipped";
    }).length;
  }

  /**
   * Read files attached in the assistant (F21.8.2) as receipts, one each, through the same
   * upload as the Add screen, which then shows them to check; the reading's id, or null
   * when the upload was refused.
   */
  async readFromChat(files: File[]): Promise<string | null> {
    this.setFromTrip(null);
    this.mode = "multiple";
    this.lines = files.map((file) => [file]);
    this.currentStep = 1;
    return (await this.submitUpload()) ? this.jobId : null;
  }

  // Legacy method for existing tests/components
  async uploadFile(file: File): Promise<boolean> {
    this.addFiles([file]);
    return this.submitUpload();
  }

  /**
   * Submits the user's decision (store or skip) for a flagged duplicate receipt.
   * Resolves the extraction server-side so it can proceed or be discarded.
   *
   * A skipped receipt leaves the selection, so it is not offered for storing; when it was
   * the last one left to store, the upload starts over instead of showing an empty step.
   */
  async resolveDuplicate(index: number, action: "store" | "skip"): Promise<boolean> {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-duplicate", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: index, action },
      });
      if (res.error)
        throw new Error(errorMessage(res.error, i18n.t("messages:upload.duplicateFailed")));
      runInAction(() => {
        this.extractedData = res.data.extracted_data ?? null;
        if (action !== "skip") return;
        this.selectedIndices.delete(index);
        if (this.receiptsToStore === 0) this.startOver();
      });
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:upload.duplicateFailed"));
    }
  }

  /**
   * Overrides an automatic position match decision (BRD B7).
   */
  async resolvePositionMatch(
    extractionIndex: number,
    matchIndex: number,
    action: "same" | "different",
  ): Promise<boolean> {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-position-match", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, match_index: matchIndex, action },
      });
      if (res.error)
        throw new Error(errorMessage(res.error, i18n.t("messages:upload.matchFailed")));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:upload.matchFailed"));
    }
  }
  get conflictsCount(): number {
    if (!this.extractedData) return 0;
    const payload = this.extractedData;
    const extractions = (payload.extractions ?? []) as Record<string, unknown>[];
    let count = 0;
    for (let i = 0; i < extractions.length; i++) {
      if (!this.selectedIndices.has(i)) continue;

      const extraction = extractions[i];
      if (!extraction) continue;

      if (extraction.is_duplicate && !extraction.duplicate_resolved) {
        count++;
      }
      if (totalNeedsDecision(extraction)) {
        count++;
      }
      const positionMatches = (extraction.position_matches ?? []) as Record<string, unknown>[];
      for (const match of positionMatches) {
        if (match.result !== "same" && match.result !== "different") {
          count++;
        }
      }
    }
    return count;
  }

  async resolveTotal(extractionIndex: number, receiptTotal: string): Promise<boolean> {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-total", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, receipt_total: receiptTotal },
      });
      if (res.error)
        throw new Error(errorMessage(res.error, i18n.t("messages:upload.totalFailed")));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:upload.totalFailed"));
    }
  }

  /**
   * Set a receipt's purchase date before it is stored (BRD A11, D3): for one that showed
   * no date and was given its upload day, or one whose date was misread. `date` is
   * YYYY-MM-DD.
   */
  async resolveDate(extractionIndex: number, date: string): Promise<boolean> {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/resolve-date", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, transaction_date: date },
      });
      if (res.error) throw new Error(errorMessage(res.error, i18n.t("messages:upload.dateFailed")));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:upload.dateFailed"));
    }
  }

  /**
   * Correct one line item the parser misread, before anything is stored.
   *
   * Only the fields given are sent: the backend leaves the rest as parsed, and
   * an empty string clears a price rather than setting it to zero. The response
   * carries the recomputed totals, so the footer and the commit gate update
   * from the same round trip.
   */
  async updateLineItem(
    extractionIndex: number,
    itemIndex: number,
    values: { name?: string; quantity?: string; unit_price?: string; total_price?: string },
  ) {
    if (!this.jobId) return false;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/line-item", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, item_index: itemIndex, ...values },
      });
      if (res.error) throw new Error(errorMessage(res.error, i18n.t("messages:upload.lineFailed")));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:upload.lineFailed"));
    }
  }

  /**
   * Add the discount the reader missed, as one "Rabat" line, so the receipt adds up
   * to what was paid (BRD A9). `amount` is what came off, as a positive number.
   */
  async addDiscount(extractionIndex: number, amount: number): Promise<boolean> {
    if (!this.jobId || this.isAddingDiscount) return false;
    this.isAddingDiscount = true;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/discount", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, amount: (-amount).toFixed(2) },
      });
      if (res.error)
        throw new Error(errorMessage(res.error, i18n.t("messages:upload.discountFailed")));
      runInAction(() => {
        if (res.data.extracted_data) {
          this.extractedData = res.data.extracted_data;
        }
      });
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:upload.discountFailed"));
    } finally {
      runInAction(() => {
        this.isAddingDiscount = false;
      });
    }
  }

  /**
   * Put back what was printed on a line the user's memory corrected (F15.3.2);
   * `forget` also stops the shop's later receipts being corrected that way.
   */
  async undoCorrection(
    extractionIndex: number,
    itemIndex: number,
    forget: boolean,
  ): Promise<boolean> {
    if (!this.jobId || this.isUndoingCorrection) return false;
    this.isUndoingCorrection = true;
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/undo-correction", {
        params: { path: { job_id: this.jobId } },
        body: { extraction_index: extractionIndex, item_index: itemIndex, forget },
      });
      if (res.error)
        throw new Error(errorMessage(res.error, i18n.t("messages:corrections.undoFailed")));
      runInAction(() => {
        if (res.data.extracted_data) this.extractedData = res.data.extracted_data;
      });
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:corrections.undoFailed"));
    } finally {
      runInAction(() => {
        this.isUndoingCorrection = false;
      });
    }
  }

  /**
   * Store the selected receipts and start the wizard afresh for the next one (F4.7).
   *
   * Stays on the upload page rather than leaving it: receipts are usually added
   * several in a row. The server re-checks every gate, so a refusal is shown
   * rather than swallowed; the button is disabled meanwhile so one click stores once.
   */
  /**
   * The receipts about to be stored that are dated outside this month, as their months:
   * stored by their own date, they do not show in this month's figures (F24.3).
   */
  private storedInOtherMonths(): { first: Date; link: string }[] {
    const extractions = (this.extractedData?.extractions ?? []) as {
      transaction_date?: string | null;
    }[];
    const thisMonth = isoDay(new Date()).slice(0, 7);
    const months: { first: Date; link: string }[] = [];
    for (const index of this.selectedIndices) {
      const day = extractions[index]?.transaction_date;
      if (!day || day.slice(0, 7) === thisMonth) continue;
      const first = new Date(`${day.slice(0, 7)}-01T00:00:00`);
      const last = new Date(first.getFullYear(), first.getMonth() + 1, 0);
      months.push({
        first,
        link: `/receipts?start=${isoDay(first)}&end=${isoDay(last)}`,
      });
    }
    return months;
  }

  async commitJob(): Promise<boolean> {
    if (!this.jobId || this.isCommitting) return false;
    this.isCommitting = true;
    const stored = this.receiptsToStore;
    const elsewhere = this.storedInOtherMonths();
    try {
      const res = await this.api.POST("/receipts/upload/{job_id}/commit", {
        params: { path: { job_id: this.jobId } },
        body: { indices_to_store: Array.from(this.selectedIndices), trips: this.tripChoices },
      });
      if (res.error)
        throw new Error(errorMessage(res.error, i18n.t("messages:upload.storeFailed")));
      runInAction(() => {
        this.startOver();
      });
      const month = elsewhere[0];
      if (month) {
        // A receipt dated in another month is stored there: say where (F24.3).
        const name = dateFormat({ month: "long", year: "numeric" }).format(month.first);
        this.toastStore?.showSuccess(
          i18n.t("messages:upload.storedElsewhere", { count: elsewhere.length, month: name }),
          { to: month.link, label: i18n.t("messages:upload.openMonth", { month: name }) },
        );
      } else {
        this.toastStore?.showSuccess(i18n.t("messages:upload.stored", { count: stored }));
      }
      this.onReceiptsStored();
      return true;
    } catch (err) {
      return this.report(err, i18n.t("messages:upload.storeFailed"));
    } finally {
      runInAction(() => {
        this.isCommitting = false;
      });
    }
  }
}
