import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { ContactForm } from "./ContactForm";

/** The areas of the Help page and their questions, in the order they are shown. */
const AREAS = {
  receipts: ["photo", "long", "email", "manual", "limit", "foreign"],
  categories: ["how", "fix", "rules"],
  goals: ["kinds", "advice"],
  household: ["share", "private"],
  trips: ["kinds", "perdiem", "settlement"],
  data: ["export", "photos", "delete"],
  account: ["confirm", "password", "install"],
} as const;

type Area = keyof typeof AREAS;

/**
 * Answers to the usual questions by area, and a way to write when there is none
 * (F17.10). Public and prerendered; every answer has its own address, `/help#trips-perdiem`.
 */
export function HelpPage() {
  const { t } = useTranslation("help");
  const { hash } = useLocation();

  // The router does not scroll to an anchor by itself: an answer linked to opens at it.
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [hash]);

  return (
    <article className="mx-auto flex w-full max-w-2xl flex-col gap-8 py-6 md:py-10">
      <header className="flex flex-col gap-2">
        <h1 className="m-0 text-[24px] font-bold text-foreground md:text-3xl">{t("title")}</h1>
        <p className="m-0 text-lg leading-relaxed text-muted-foreground">{t("intro")}</p>
        <nav aria-label={t("title")} className="flex flex-wrap gap-x-4 gap-y-1 pt-1">
          {(Object.keys(AREAS) as Area[]).map((area) => (
            <a
              key={area}
              href={`#${area}`}
              className="inline-flex min-h-11 items-center text-md text-primary hover:underline md:min-h-0"
            >
              {t(`areas.${area}.title`)}
            </a>
          ))}
        </nav>
      </header>

      {(Object.keys(AREAS) as Area[]).map((area) => (
        <section key={area} id={area} className="flex flex-col gap-4 scroll-mt-4">
          <h2 className="m-0 text-xl font-semibold text-foreground">{t(`areas.${area}.title`)}</h2>
          {AREAS[area].map((item) => {
            const id = `${area}-${item}`;
            const key = `areas.${area}.items.${item}` as "areas.receipts.items.photo";
            return (
              <section key={item} id={id} className="flex flex-col gap-1.5 scroll-mt-4">
                <h3 className="m-0 text-lg font-semibold text-foreground">
                  <a href={`#${id}`} className="text-foreground no-underline hover:underline">
                    {t(`${key}.q`)}
                  </a>
                </h3>
                <p className="m-0 text-md leading-relaxed text-foreground">{t(`${key}.a`)}</p>
              </section>
            );
          })}
        </section>
      ))}

      <ContactForm />
    </article>
  );
}
