import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";

export type Conversation = components["schemas"]["ConversationRead"];
export type ConversationSummary = components["schemas"]["ConversationSummary"];
export type ChatMessage = components["schemas"]["MessageRead"];
export type ChatCard = components["schemas"]["CardRead"];

/**
 * The conversations with the assistant (F21.1): the list, the one open, sending to it, and
 * the cards it proposes — saved only when the user approves them, as they left the fields
 * (F21.7, ADR-0025).
 */
export class AssistantStore {
  conversations: ConversationSummary[] = [];
  open: Conversation | null = null;
  /** What the user sent and the assistant has not answered yet, oldest first: shown at once,
   * and sent one after another so each lands in the same conversation. */
  pending: string[] = [];
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
    makeAutoObservable<this, "api" | "toastStore" | "onSaved">(
      this,
      { api: false, toastStore: false, onSaved: false },
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
  send(text: string, today: string): boolean {
    const trimmed = text.trim();
    if (!trimmed) return false;
    this.pending.push(trimmed);
    if (!this.sendState.isLoading) void this.drain(today);
    return true;
  }

  private async drain(today: string): Promise<void> {
    this.sendState.start();
    for (let text = this.pending.at(0); text !== undefined; text = this.pending.at(0)) {
      const response = await settle(() =>
        this.api.POST("/api/v1/assistant/messages", {
          body: { text, conversation_id: this.open?.id ?? null, today },
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
