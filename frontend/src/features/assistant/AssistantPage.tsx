import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { List, Loader2, Mic, Paperclip, Plus, SendHorizontal, Square, X } from "lucide-react";

import { dateFormat } from "@/i18n/format";
import { Button } from "@/shared/components";
import { canRecord } from "@/shared/speech";
import { useStores } from "@/stores/StoreContext";
import { AnswerCard } from "./components/AnswerCard";
import { AttachmentCard } from "./components/AttachmentCard";
import { ApproveCard } from "./components/ApproveCard";
import { ChoiceCard } from "./components/ChoiceCard";
import { RecordingTimer } from "./components/RecordingTimer";
import { Thinking } from "./components/Thinking";
import { FormCard } from "./components/FormCard";

const WHEN = dateFormat({ day: "numeric", month: "short" });

/**
 * The assistant (F21.1, F21.7): ask about spending — answered with a chart and a link to
 * the screen where it fits (F21.4) — or say what to record, change or remove: each comes
 * as a card, the app's own for the commonest and one drawn from its form for the rest. Messages may be
 * sent one after another; each is answered in turn. What it proposes comes as cards, saved
 * only when approved. The microphone records what is said and puts the recognised words
 * in the field (F21.2.2); the paperclip attaches receipts, read as from the Add screen
 * (F21.8.2). When something could mean more than one thing the assistant asks with
 * options to tap (F21.13.3). Conversations are kept and listed,
 * newest first, each reopened where it was left — beside the chat on a desktop, behind a
 * button on a phone.
 */
export const AssistantPage = observer(function AssistantPage() {
  const {
    assistantStore,
    budgetStore,
    categoriesStore,
    bankAccountsStore,
    uploadStore,
    quotaStore,
  } = useStores();
  const { t } = useTranslation("assistant");
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const picker = useRef<HTMLInputElement>(null);
  const [listing, setListing] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const today = budgetStore.today;
  const open = assistantStore.open;
  const messages = open?.messages ?? [];

  useEffect(() => {
    void assistantStore.loadConversations();
    // An expense card picks from the user's categories (F21.3).
    if (categoriesStore.categories.length === 0) void categoriesStore.fetchCategories();
    // An income card says when approving it makes the first card (F23.21).
    if (!bankAccountsStore.loaded) void bankAccountsStore.load(budgetStore.today);
  }, [assistantStore, categoriesStore, bankAccountsStore, budgetStore]);
  useEffect(() => {
    // Every answer spends AI credits (F21.9): what is left follows the conversation.
    void quotaStore.load();
  }, [quotaStore, messages.length]);
  useEffect(() => {
    // Not every environment scrolls (tests); the newest message is a nicety there.
    if ("scrollIntoView" in (end.current ?? {})) end.current?.scrollIntoView({ block: "end" });
  }, [messages.length, assistantStore.pending.length]);

  const send = (said: string) => {
    if (files.length === 0) {
      if (assistantStore.send(said, today)) setText("");
      return;
    }
    const attached = files;
    const words = said.trim() || t("attach.text");
    setFiles([]);
    setText("");
    void uploadStore.readFromChat(attached).then((jobId) => {
      if (jobId) assistantStore.send(words, today, { jobId, count: attached.length });
    });
  };

  const dictate = async () => {
    if (assistantStore.dictation === "listening") {
      const said = await assistantStore.finishDictation();
      if (said) setText((typed) => (typed.trim() ? `${typed.trim()} ${said}` : said));
    } else {
      await assistantStore.startDictation();
    }
  };

  const list = (
    <nav aria-label={t("conversations")} className="flex flex-col gap-2">
      <Button
        variant="secondary"
        className="min-h-11"
        onClick={() => {
          assistantStore.startNew();
          setListing(false);
        }}
      >
        <Plus size={16} aria-hidden="true" />
        {t("new")}
      </Button>
      <ul className="m-0 flex list-none flex-col gap-1 p-0">
        {assistantStore.conversations.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              aria-current={open?.id === c.id ? "true" : undefined}
              onClick={() => {
                void assistantStore.openConversation(c.id);
                setListing(false);
              }}
              className={`flex min-h-12 w-full flex-col justify-center rounded-control px-3 py-2 text-left ${
                open?.id === c.id ? "bg-tone-primary-bg" : "hover:bg-muted"
              }`}
            >
              <span className="w-full truncate text-md font-bold">{c.title}</span>
              <span className="text-sm text-muted-foreground">
                {WHEN.format(new Date(c.updated_at))}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );

  return (
    <div className="mx-auto grid w-full max-w-5xl flex-1 gap-4 py-4 md:py-2 lg:grid-cols-[16rem_1fr]">
      <aside className="hidden lg:block">{list}</aside>

      <section
        aria-labelledby="assistant-title"
        className="flex min-h-[70vh] min-w-0 flex-col gap-3"
      >
        <div className="flex items-center gap-3">
          <h1
            id="assistant-title"
            className="m-0 mr-auto text-3xl font-extrabold tracking-[-0.02em]"
          >
            {t("title")}
          </h1>
          <button
            type="button"
            aria-label={t("conversations")}
            aria-expanded={listing}
            onClick={() => {
              setListing((v) => !v);
            }}
            className="control-fill flex h-11 w-11 items-center justify-center rounded-pill lg:hidden"
          >
            <List size={20} aria-hidden="true" />
          </button>
        </div>

        {listing ? (
          <div className="rounded-card bg-surface p-3 lg:hidden">{list}</div>
        ) : (
          <>
            <ol className="m-0 flex flex-1 list-none flex-col gap-3 p-0" aria-live="polite">
              {messages.length === 0 && assistantStore.pending.length === 0 && (
                <li className="flex flex-col gap-3 rounded-card bg-surface p-5">
                  <h2 className="m-0 text-xl font-extrabold">{t("empty.title")}</h2>
                  <p className="m-0 text-md leading-relaxed text-muted-foreground">
                    {t("empty.body")}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {t("examples", { returnObjects: true }).map((example) => (
                      <button
                        key={example}
                        type="button"
                        onClick={() => {
                          send(example);
                        }}
                        className="min-h-11 rounded-pill bg-tone-primary-bg px-3.5 text-md font-bold text-primary"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </li>
              )}
              {messages.map((m, i) =>
                m.card?.kind === "attachment" ? (
                  <li key={m.id} className="flex max-w-full flex-col md:max-w-[85%] md:self-end">
                    <AttachmentCard message={m} />
                  </li>
                ) : m.card?.kind === "choice" ? (
                  <li key={m.id} className="w-full min-w-0 md:max-w-[85%]">
                    <ChoiceCard
                      message={m}
                      answered={i < messages.length - 1 || assistantStore.pending.length > 0}
                      onChoose={send}
                    />
                  </li>
                ) : m.card?.kind === "answer" ? (
                  <li key={m.id} className="w-full min-w-0 md:max-w-[85%]">
                    <AnswerCard message={m} />
                  </li>
                ) : m.card?.form ? (
                  <li key={m.id} className="max-w-full md:max-w-[85%]">
                    <FormCard message={m} today={today} />
                  </li>
                ) : m.card ? (
                  <li key={m.id} className="max-w-full md:max-w-[85%]">
                    <ApproveCard message={m} today={today} />
                  </li>
                ) : (
                  <li
                    key={m.id}
                    className={`max-w-[85%] rounded-card px-4 py-2.5 text-lg leading-relaxed whitespace-pre-wrap ${
                      m.role === "user"
                        ? "self-end bg-primary text-primary-foreground"
                        : "self-start bg-surface"
                    }`}
                  >
                    {m.text || t("failed")}
                  </li>
                ),
              )}
              {assistantStore.pending.map((waiting, i) => (
                <li
                  key={`${String(i)}-${waiting.text}`}
                  className="max-w-[85%] self-end rounded-card bg-primary px-4 py-2.5 text-lg whitespace-pre-wrap text-primary-foreground"
                >
                  {waiting.text}
                </li>
              ))}
              {assistantStore.pending.length > 0 && (
                <li className="self-start rounded-card bg-surface px-4 py-2.5 text-lg text-muted-foreground">
                  <Thinking />
                </li>
              )}
            </ol>
            <div ref={end} />

            <form
              className="sticky bottom-24 flex flex-col gap-2 rounded-card bg-surface p-2 md:bottom-4"
              onSubmit={(event) => {
                event.preventDefault();
                send(text);
              }}
            >
              {files.length > 0 && (
                <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                  {files.map((file, i) => (
                    <li
                      key={`${String(i)}-${file.name}`}
                      className="flex min-h-11 max-w-full items-center gap-1 rounded-pill bg-muted pr-1 pl-3 text-md"
                    >
                      <Paperclip size={14} aria-hidden="true" className="shrink-0" />
                      <span className="min-w-0 truncate">{file.name}</span>
                      <button
                        type="button"
                        aria-label={t("attach.remove", { name: file.name })}
                        onClick={() => {
                          setFiles((all) => all.filter((_, j) => j !== i));
                        }}
                        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-pill"
                      >
                        <X size={16} aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {assistantStore.dictation !== "idle" && (
                <p
                  className="m-0 inline-flex items-center gap-2 px-1 text-md text-muted-foreground"
                  aria-live="polite"
                >
                  {assistantStore.dictation === "listening" ? (
                    <span
                      className="h-2.5 w-2.5 animate-pulse rounded-pill bg-error"
                      aria-hidden="true"
                    />
                  ) : (
                    <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                  )}
                  {assistantStore.dictation === "listening"
                    ? t("mic.listening")
                    : t("mic.recognising")}
                  {assistantStore.listeningSince !== null && (
                    <RecordingTimer since={assistantStore.listeningSince} />
                  )}
                </p>
              )}
              <div className="flex items-end gap-2">
                <input
                  ref={picker}
                  type="file"
                  multiple
                  accept="image/jpeg, image/png, image/heic, application/pdf"
                  className="hidden"
                  onChange={(e) => {
                    const chosen = Array.from(e.target.files ?? []);
                    setFiles((all) => [...all, ...chosen]);
                    e.target.value = "";
                  }}
                />
                <button
                  type="button"
                  aria-label={t("attach.button")}
                  onClick={() => picker.current?.click()}
                  className="control-fill flex h-11 w-11 shrink-0 items-center justify-center rounded-pill"
                >
                  <Paperclip size={20} aria-hidden="true" />
                </button>
                <label htmlFor="assistant-input" className="sr-only">
                  {t("placeholder")}
                </label>
                <textarea
                  id="assistant-input"
                  rows={1}
                  value={text}
                  maxLength={2000}
                  placeholder={t("placeholder")}
                  onChange={(e) => {
                    setText(e.target.value);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send(text);
                    }
                  }}
                  className="control-fill min-h-11 min-w-0 flex-1 resize-none rounded-control px-3 py-2.5 text-lg"
                />
                {/* As in a messenger: the microphone while there is nothing to send. */}
                {canRecord() &&
                (assistantStore.dictation !== "idle" || (!text.trim() && files.length === 0)) ? (
                  <button
                    type="button"
                    aria-label={
                      assistantStore.dictation === "listening" ? t("mic.stop") : t("mic.start")
                    }
                    aria-pressed={assistantStore.dictation === "listening"}
                    disabled={assistantStore.dictation === "recognising"}
                    onClick={() => void dictate()}
                    className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-pill disabled:opacity-50 ${
                      assistantStore.dictation === "listening"
                        ? "bg-error text-primary-foreground"
                        : "bg-primary text-primary-foreground"
                    }`}
                  >
                    {assistantStore.dictation === "listening" ? (
                      <Square size={18} aria-hidden="true" />
                    ) : (
                      <Mic size={20} aria-hidden="true" />
                    )}
                  </button>
                ) : (
                  <button
                    type="submit"
                    aria-label={t("send")}
                    disabled={!text.trim() && files.length === 0}
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-pill bg-primary text-primary-foreground disabled:opacity-50"
                  >
                    <SendHorizontal size={20} aria-hidden="true" />
                  </button>
                )}
              </div>
              {quotaStore.quota && !quotaStore.quota.unlimited && (
                <p className="m-0 px-1 text-sm text-muted-foreground tabular-nums">
                  {t("creditsLeft", {
                    receipts: quotaStore.quota.receipts_left ?? 0,
                    messages: quotaStore.quota.messages_left ?? 0,
                  })}
                </p>
              )}
            </form>
          </>
        )}
      </section>
    </div>
  );
});
