import { useTranslation } from "react-i18next";

import { dateFormat } from "@/i18n/format";
import { PublicLinks } from "@/shared/components";

/** The day the current terms and privacy policy took effect; backend `app/domain/terms.py`. */
export const TERMS_VERSION = "2026-10-22";

const SECTIONS = {
  privacy: ["who", "data", "why", "ai", "where", "keep", "storage", "rights"],
  terms: ["service", "account", "content", "use", "end", "law"],
} as const;

const DAY = dateFormat({ day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

/**
 * The privacy policy or the terms of use (F17.9.4), public and in the reader's language.
 * What they say rests on the record of processing in ADR-0020; F17.7 finalises them.
 */
export function LegalPage({ document: doc }: { document: keyof typeof SECTIONS }) {
  const { t } = useTranslation("legal");
  return (
    <article className="mx-auto flex w-full max-w-2xl flex-col gap-6 py-6 md:py-10">
      <header className="flex flex-col gap-2">
        <h1 className="m-0 text-[24px] font-bold text-foreground md:text-3xl">
          {t(`${doc}.title`)}
        </h1>
        <p className="m-0 text-lg leading-relaxed text-muted-foreground">{t(`${doc}.intro`)}</p>
        <p className="m-0 text-base text-muted-foreground">
          {t("version", { date: DAY.format(new Date(`${TERMS_VERSION}T00:00:00Z`)) })}
        </p>
      </header>
      {SECTIONS[doc].map((section) => (
        <section key={section} className="flex flex-col gap-2">
          <h2 className="m-0 text-xl font-semibold text-foreground">
            {t(`${doc}.sections.${section}.title` as "privacy.sections.data.title")}
          </h2>
          {t(`${doc}.sections.${section}.body` as "privacy.sections.data.body")
            .split("\n\n")
            .map((paragraph) => (
              <p key={paragraph} className="m-0 text-md leading-relaxed text-foreground">
                {paragraph}
              </p>
            ))}
        </section>
      ))}
      <footer className="border-t border-border pt-6">
        <PublicLinks />
      </footer>
    </article>
  );
}
