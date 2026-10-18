import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Card, Input, Note } from "@/shared/components";
import type { ContactTopic } from "@/stores/ContactStore";
import { useStores } from "@/stores/StoreContext";

const TOPICS: ContactTopic[] = ["question", "problem", "idea", "data"];
/** The support mailbox (F22.1.2), public as in the store listing; backend SUPPORT_EMAIL. */
export const SUPPORT_EMAIL = "bohdan.razhyk.support@gmail.com";

/**
 * Writing to the people running the service (F17.10.2). A signed-in user's address is
 * filled in; the hidden "website" field is left empty by people and filled by bots.
 */
export const ContactForm = observer(function ContactForm() {
  const { contactStore, authStore } = useStores();
  const { t } = useTranslation("help");
  const [email, setEmail] = useState(authStore.user?.email ?? "");
  const [topic, setTopic] = useState<ContactTopic>("question");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState("");
  const { state } = contactStore;

  // A message sent earlier is not this visit's: the form opens empty.
  useEffect(() => {
    contactStore.reset();
  }, [contactStore]);

  return (
    <section id="contact" className="scroll-mt-4">
      <Card variant="surface" className="flex flex-col gap-4 p-4 md:p-6">
        <div className="flex flex-col gap-1">
          <h2 className="m-0 text-xl font-semibold">{t("contact.title")}</h2>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">{t("contact.intro")}</p>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">
            {t("contact.direct")}{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="break-all text-primary hover:underline">
              {SUPPORT_EMAIL}
            </a>
            .
          </p>
        </div>
        {state.status === "success" ? (
          <>
            <Note tone="success">{t("contact.sent")}</Note>
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto md:self-start"
              onClick={() => {
                setMessage("");
                contactStore.reset();
              }}
            >
              {t("contact.another")}
            </Button>
          </>
        ) : (
          <form
            className="flex flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              void contactStore.send(email, topic, message, website);
            }}
          >
            {state.error && <Note tone="error">{state.error}</Note>}
            <Input
              id="contact-email"
              type="email"
              autoComplete="email"
              label={t("contact.email")}
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
              }}
              required
            />
            <div className="flex flex-col gap-1.5">
              <label htmlFor="contact-topic" className="text-sm font-medium text-muted-foreground">
                {t("contact.topic")}
              </label>
              <select
                id="contact-topic"
                className="min-h-11 rounded-control border-2 border-transparent control-fill px-3 py-2 text-base text-foreground"
                value={topic}
                onChange={(event) => {
                  setTopic(event.target.value as ContactTopic);
                }}
              >
                {TOPICS.map((value) => (
                  <option key={value} value={value}>
                    {t(`contact.topics.${value}`)}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="contact-message"
                className="text-sm font-medium text-muted-foreground"
              >
                {t("contact.message")}
              </label>
              <textarea
                id="contact-message"
                rows={6}
                minLength={10}
                maxLength={4000}
                className="rounded-control border-2 border-transparent control-fill px-3 py-2 text-base text-foreground"
                value={message}
                onChange={(event) => {
                  setMessage(event.target.value);
                }}
                required
              />
            </div>
            {/* Hidden from people and screen readers; a bot filling every field fills it. */}
            <input
              type="text"
              name="website"
              tabIndex={-1}
              autoComplete="off"
              aria-hidden="true"
              className="hidden"
              value={website}
              onChange={(event) => {
                setWebsite(event.target.value);
              }}
            />
            <Button
              type="submit"
              className="w-full md:w-auto md:self-start"
              disabled={state.isLoading}
            >
              {state.isLoading ? t("contact.sending") : t("contact.send")}
            </Button>
          </form>
        )}
      </Card>
    </section>
  );
});
