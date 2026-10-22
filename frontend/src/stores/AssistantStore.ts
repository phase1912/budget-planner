import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { isApproval, record, type Recording } from "@/shared/speech";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";

export type Conversation = components["schemas"]["ConversationRead"];
export type ConversationSummary = components["schemas"]["ConversationSummary"];
export type ChatMessage = components["schemas"]["MessageRead"];
export type ChatCard = components["schemas"]["CardRead"];

/** Receipt files sent with a message: the reading the upload started, and how many. */
export interface Attached {
  jobId: string;
  count: number;
}

/** A message the assistant has not answered yet. */
export interface Waiting {
  text: string;
  attached: Attached | null;
}

/**
 * The conversations with the assistant (F21.1): the list, the one open, sending to it, and
 * the cards it proposes — saved only when the user approves them, as they left the fields
 * (F21.7, ADR-0025). The microphone is recorded and recognised by the service (F21.2.2):
 * the words land in the field to send or correct, and "approve" saves the waiting card.
 */
export class AssistantStore {
  conversations: ConversationSummary[] = [];
  open: Conversation | null = null;
  /** What the user sent and the assistant has not answered yet, oldest first: shown at once,
   * and sent one after another so each lands in the same conversation. */
  pending: Waiting[] = [];
  /** Where dictation is: off, listening to the microphone, or waiting for the words. */
  dictation: "idle" | "listening" | "recognising" = "idle";
  /** When listening began, for the timer beside the microphone (F21.9.4). */
  listeningSince: number | null = null;
  private recording: Recording | null = null;
  /** Bumped when the user says "approve": the waiting card saves itself as it stands. */
  approveSignal = 0;
  readonly state = new AsyncState();
  readonly sendState = new AsyncState();
  private readonly api: ApiClient;
  private readonly toastStore: ToastStore;
  private readonly onSaved: () => void;

  constructor(api: ApiClient, toastStore: ToastStore, onSaved: () => void = () => undefined) {
    this.api = api;
    this.toastStore = toastStore;
    this.onSaved = onSaved;
    makeAutoObservable<this, "api" | "toastStore" | "onSaved" | "recording">(
      this,
      { api: false, toastStore: false, onSaved: false, recording: false },
      { autoBind: true },
    );
  }

  /** The latest card still waiting for the user, which "approve" by voice saves. */
  get waitingCard(): ChatMessage | null {
    const messages = this.open?.messages ?? [];
    return [...messages].reverse().find((m) => m.card_state === "proposed") ?? null;
  }

  /** "Approve" said aloud (F21.7): the latest waiting card saves its fields as they are. */
  approveByVoice(): void {
    if (this.waitingCard) this.approveSignal++;
  }

  async loadConversations(): Promise<void> {
    this.state.start();
    const response = await settle(() => this.api.GET("/api/v1/assistant/conversations"));
    runInAction(() => {
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:assistant.loadFailed")));
        return;
      }
      this.conversations = response.data;
      this.state.succeed();
    });
  }

  async openConversation(id: string): Promise<void> {
    const response = await settle(() =>
      this.api.GET("/api/v1/assistant/conversations/{conversation_id}", {
        params: { path: { conversation_id: id } },
      }),
    );
    runInAction(() => {
      if (response.error === undefined) this.open = response.data;
    });
  }

  /** Start afresh: the next message opens a new conversation. */
  startNew(): void {
    this.open = null;
  }

  /** Send what the user wrote or said. It joins the queue at once, so the user may go on
   * writing; each answer and its cards replace the open conversation. */
  send(text: string, today: string, attached: Attached | null = null): boolean {
    const trimmed = text.trim();
    if (!trimmed) return false;
    this.pending.push({ text: trimmed, attached });
    if (!this.sendState.isLoading) void this.drain(today);
    return true;
  }

  private async drain(today: string): Promise<void> {
    this.sendState.start();
    for (let next = this.pending.at(0); next !== undefined; next = this.pending.at(0)) {
      const { text, attached } = next;
      const response = await settle(() =>
        this.api.POST("/api/v1/assistant/messages", {
          body: {
            text,
            conversation_id: this.open?.id ?? null,
            today,
            upload_job_id: attached?.jobId ?? null,
            attached: attached?.count ?? 0,
          },
        }),
      );
      const ok = runInAction(() => {
        this.pending.shift();
        if (response.error !== undefined) {
          const message = errorMessage(response.error, i18n.t("messages:assistant.sendFailed"));
          this.sendState.fail(message);
          this.toastStore.showError(message);
          return false;
        }
        this.open = response.data;
        return true;
      });
      if (!ok) {
        // What was queued after a failure would land out of order: the user sends it again.
        runInAction(() => {
          this.pending = [];
        });
        return;
      }
    }
    runInAction(() => {
      this.sendState.succeed();
    });
    void this.loadConversations();
  }

  /** Start listening to the microphone; false when the browser or the user refuses it. */
  async startDictation(): Promise<boolean> {
    if (this.dictation !== "idle") return false;
    try {
      const recording = await record(() => {
        void this.finishDictation();
      });
      runInAction(() => {
        this.recording = recording;
        this.dictation = "listening";
        this.listeningSince = Date.now();
      });
      return true;
    } catch {
      this.toastStore.showError(i18n.t("messages:assistant.microphoneRefused"));
      return false;
    }
  }

  /**
   * Stop listening and have what was said recognised: the words, for the field — or null
   * when there were none, they could not be had, or they were "approve", which saves the
   * waiting card instead (F21.7).
   */
  async finishDictation(): Promise<string | null> {
    const recording = this.recording;
    if (!recording || this.dictation !== "listening") return null;
    this.recording = null;
    this.dictation = "recognising";
    this.listeningSince = null;
    const sound = await recording.stop();
    const form = new FormData();
    form.append("audio", sound, "speech.wav");
    const response = await settle(() =>
      this.api.POST("/api/v1/assistant/speech", {
        // @ts-expect-error openapi-fetch types do not correctly handle FormData
        body: form,
      }),
    );
    return runInAction(() => {
      this.dictation = "idle";
      if (response.error !== undefined) {
        this.toastStore.showError(
          errorMessage(response.error, i18n.t("messages:assistant.speechFailed")),
        );
        return null;
      }
      const said = response.data.text.trim();
      if (isApproval(said) && this.waitingCard) {
        this.approveByVoice();
        return null;
      }
      return said || null;
    });
  }

  /** Drop the recording without recognising it. */
  cancelDictation(): void {
    this.recording?.cancel();
    this.recording = null;
    this.dictation = "idle";
    this.listeningSince = null;
  }

  /** Approve a card as the user left its fields: only now is anything written. */
  async save(
    message: ChatMessage,
    fields: Record<string, unknown>,
    today: string,
  ): Promise<boolean> {
    const response = await settle(() =>
      this.api.POST("/api/v1/assistant/cards/{message_id}/save", {
        params: { path: { message_id: message.id } },
        body: { fields, today },
      }),
    );
    return runInAction(() => {
      if (response.error !== undefined) {
        this.toastStore.showError(
          errorMessage(response.error, i18n.t("messages:assistant.saveFailed")),
        );
        return false;
      }
      this.replace(response.data);
      this.toastStore.showSuccess(i18n.t("messages:assistant.saved"));
      this.onSaved();
      return true;
    });
  }

  /** Turn a card down; nothing is written. */
  async dismiss(message: ChatMessage): Promise<void> {
    const response = await settle(() =>
      this.api.POST("/api/v1/assistant/cards/{message_id}/dismiss", {
        params: { path: { message_id: message.id } },
      }),
    );
    runInAction(() => {
      if (response.error === undefined) this.replace(response.data);
    });
  }

  reset(): void {
    this.conversations = [];
    this.open = null;
    this.pending = [];
  }

  private replace(message: ChatMessage): void {
    if (!this.open) return;
    this.open.messages = this.open.messages.map((m) => (m.id === message.id ? message : m));
  }
}
