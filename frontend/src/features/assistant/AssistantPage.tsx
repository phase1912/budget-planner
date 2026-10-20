import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { List, Mic, MicOff, Plus, SendHorizontal } from "lucide-react";

import { dateFormat } from "@/i18n/format";
import { Button } from "@/shared/components";
import { canListen, isApproval, listen } from "@/shared/speech";
import { useStores } from "@/stores/StoreContext";
import { ApproveCard } from "./components/ApproveCard";

const WHEN = dateFormat({ day: "numeric", month: "short" });

/**
 * The assistant (F21.1, F21.7): ask about the month or say what to record, typed or spoken —
 * speech is turned into text by the browser. What it proposes comes as cards, saved only
 * when approved; saying "approve" saves the waiting one. Conversations are kept and listed,
 * newest first, each reopened where it was left — beside the chat on a desktop, behind a
 * button on a phone.
 */
export const AssistantPage = observer(function AssistantPage() {
  const { assistantStore, budgetStore, languageStore } = useStores();
  const { t } = useTranslation("assistant");
  const [text, setText] = useState("");
  const [listing, setListing] = useState(false);
  const [listening, setListening] = useState(false);
  const stop = useRef<(() => void) | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const today = budgetStore.today;
  const open = assistantStore.open;
  const messages = open?.messages ?? [];

  useEffect(() => {
    void assistantStore.loadConversations();
  }, [assistantStore]);
  useEffect(() => {
    // Not every environment scrolls (tests); the newest message is a nicety there.
    if ("scrollIntoView" in (end.current ?? {})) end.current?.scrollIntoView({ block: "end" });
  }, [messages.length, assistantStore.pending]);

  const send = (said: string) => {
    void assistantStore.send(said, today).then((ok) => {
      if (ok) setText("");
    });
  };
  const toggleMic = () => {
    if (listening) {
      stop.current?.();
      return;
    }
    stop.current = listen(
      languageStore.language,
      (heard, final) => {
        setText(heard);
        if (!final) return;
        if (isApproval(heard) && assistantStore.waitingCard) {
          assistantStore.approveByVoice();
          setText("");
        } else {
          send(heard);
        }
      },
      () => {
        setListening(false);
      },
    );
    setListening(stop.current !== null);
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
        <div className="flex items-center justify-between gap-3">
          <h1 id="assistant-title" className="m-0 text-3xl font-extrabold tracking-[-0.02em]">
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
              {messages.length === 0 && !assistantStore.pending && (
                <li className="flex flex-col gap-3 rounded-card bg-surface p-5">
                  <h2 className="m-0 text-xl font-extrabold">{t("empty.title")}</h2>
                  <p className="m-0 text-md leading-relaxed text-muted-foreground">
                    {t("empty.body")}
                  </p>
                  {canListen() && (
                    <p className="m-0 text-sm text-muted-foreground">{t("voiceNote")}</p>
                  )}
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
              {messages.map((m) =>
                m.card ? (
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
              {assistantStore.pending && (
                <>
                  <li className="max-w-[85%] self-end rounded-card bg-primary px-4 py-2.5 text-lg text-primary-foreground">
                    {assistantStore.pending}
                  </li>
                  <li className="self-start rounded-card bg-surface px-4 py-2.5 text-lg text-muted-foreground">
                    {t("thinking")}
                  </li>
                </>
              )}
            </ol>
            <div ref={end} />

            <form
              className="sticky bottom-24 flex items-end gap-2 rounded-card bg-surface p-2 md:bottom-4"
              onSubmit={(event) => {
                event.preventDefault();
                send(text);
              }}
            >
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
              {canListen() && (
                <button
                  type="button"
                  aria-label={listening ? t("stop") : t("listen")}
                  aria-pressed={listening}
                  onClick={toggleMic}
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-pill ${
                    listening ? "bg-error text-primary-foreground" : "control-fill text-primary"
                  }`}
                >
                  {listening ? (
                    <MicOff size={20} aria-hidden="true" />
                  ) : (
                    <Mic size={20} aria-hidden="true" />
                  )}
                </button>
              )}
              <button
                type="submit"
                aria-label={t("send")}
                disabled={!text.trim() || assistantStore.sendState.isLoading}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-pill bg-primary text-primary-foreground disabled:opacity-50"
              >
                <SendHorizontal size={20} aria-hidden="true" />
              </button>
            </form>
          </>
        )}
      </section>
    </div>
  );
});
