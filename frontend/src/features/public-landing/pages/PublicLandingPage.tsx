import { useEffect } from "react";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { LANGUAGES, LANGUAGE_NAMES, type Language } from "@/i18n/languages";
import { Button } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { FeatureSection } from "../components/FeatureSection";
import { GoalPreview } from "../components/previews/GoalPreview";
import { HouseholdPreview } from "../components/previews/HouseholdPreview";
import { IntakePreview } from "../components/previews/IntakePreview";
import { ReceiptPreview } from "../components/previews/ReceiptPreview";
import { SpendingPreview } from "../components/previews/SpendingPreview";
import { TripPreview } from "../components/previews/TripPreview";

const STEPS = ["shoot", "check", "see"] as const;

/** Sign-up and sign-in, the page's two ways forward. */
function Calls() {
  const { t } = useTranslation("landing");
  return (
    <div className="flex w-full flex-col gap-2.5 md:w-auto md:flex-row md:items-center">
      <Link to="/register" className="contents">
        <Button size="lg" className="w-full text-[15px] md:w-auto">
          {t("createAccount")}
          <ArrowRight size={17} aria-hidden="true" className="ml-2" />
        </Button>
      </Link>
      <Link to="/login" className="contents">
        <Button variant="secondary" size="lg" className="w-full text-[15px] md:w-auto">
          {t("haveOne")}
        </Button>
      </Link>
    </div>
  );
}

/**
 * What a visitor without a session sees (F9.4.2, F17.2): the promise, how it works, what
 * the product does — receipts, spending, goals, households, trips — each beside a preview
 * of its screen, a FAQ and the way in. At "/" it reads in the visitor's language; at
 * "/en", "/uk" and "/pl" in that one, which is also how it is prerendered for search
 * engines and link previews, and opening one counts as choosing its language.
 */
export function PublicLandingPage({ language }: { language?: Language }) {
  const { t } = useTranslation("landing");
  const { languageStore } = useStores();

  useEffect(() => {
    if (language && languageStore.language !== language) void languageStore.choose(language);
  }, [language, languageStore]);

  const faq = t("faq.items", { returnObjects: true }) as { q: string; a: string }[];

  return (
    <div className="flex w-full flex-grow flex-col items-center gap-16 py-8 md:gap-24 md:py-14">
      <section
        aria-labelledby="landing-title"
        className="grid w-full max-w-[1080px] grid-cols-1 items-center gap-10 lg:grid-cols-[1.1fr_1fr] lg:gap-14"
      >
        <div className="flex flex-col items-start gap-5">
          <h1
            id="landing-title"
            className="m-0 text-[34px] font-bold leading-[1.12] tracking-[-0.02em] md:text-[46px]"
          >
            {t("title1")}
            <br />
            {t("title2")}
          </h1>
          <p className="m-0 max-w-[560px] text-[17px] leading-[1.6] text-muted-foreground text-pretty">
            {t("lead")}
          </p>
          <Calls />
          <p className="m-0 text-base text-muted-foreground">{t("free")}</p>
        </div>
        <ReceiptPreview />
      </section>

      <ol className="m-0 grid w-full max-w-[1080px] list-none grid-cols-1 gap-6 border-t border-border p-0 pt-10 md:grid-cols-3">
        {STEPS.map((step, i) => (
          <li key={step} className="flex flex-col gap-2.5">
            <span
              aria-hidden="true"
              className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-primary text-[12px] font-bold text-primary-foreground"
            >
              {i + 1}
            </span>
            <span className="text-lg font-semibold">{t(`steps.${step}.title`)}</span>
            <span className="text-md leading-relaxed text-muted-foreground">
              {t(`steps.${step}.text`)}
            </span>
          </li>
        ))}
      </ol>

      <section
        aria-labelledby="landing-features"
        className="flex w-full max-w-[1080px] flex-col gap-14 md:gap-20"
      >
        <h2
          id="landing-features"
          className="m-0 text-center text-[26px] font-bold tracking-[-0.02em] md:text-[32px]"
        >
          {t("features.title")}
        </h2>
        <FeatureSection feature="receipts" preview={<IntakePreview />} />
        <FeatureSection feature="spending" preview={<SpendingPreview />} flip />
        <FeatureSection feature="goals" preview={<GoalPreview />} />
        <FeatureSection feature="household" preview={<HouseholdPreview />} flip />
        <FeatureSection feature="trips" preview={<TripPreview />} />
      </section>

      <section
        aria-labelledby="landing-privacy"
        className="flex w-full max-w-[760px] flex-col gap-2 rounded-card bg-muted p-6 text-center md:p-8"
      >
        <h2 id="landing-privacy" className="m-0 text-[22px] font-bold">
          {t("privacyTitle")}
        </h2>
        <p className="m-0 text-lg leading-[1.6] text-muted-foreground">{t("privacy")}</p>
      </section>

      <section aria-labelledby="landing-faq" className="flex w-full max-w-[760px] flex-col gap-4">
        <h2
          id="landing-faq"
          className="m-0 text-[26px] font-bold tracking-[-0.02em] md:text-[32px]"
        >
          {t("faq.title")}
        </h2>
        <div className="flex flex-col divide-y divide-border rounded-card border border-border">
          {faq.map((item) => (
            <details key={item.q} className="group px-4 md:px-5">
              <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 py-3 text-lg font-semibold">
                {item.q}
                <ArrowRight
                  size={16}
                  aria-hidden="true"
                  className="shrink-0 text-muted-foreground transition-transform group-open:rotate-90"
                />
              </summary>
              <p className="m-0 pb-4 text-md leading-[1.6] text-muted-foreground">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section
        aria-labelledby="landing-final"
        className="flex w-full max-w-[760px] flex-col items-center gap-4 text-center"
      >
        <h2
          id="landing-final"
          className="m-0 text-[26px] font-bold tracking-[-0.02em] md:text-[32px]"
        >
          {t("final.title")}
        </h2>
        <p className="m-0 text-lg text-muted-foreground">{t("final.text")}</p>
        <Calls />
      </section>

      <footer className="flex w-full max-w-[1080px] flex-col items-center gap-2 border-t border-border pt-6 text-center">
        <nav aria-label={t("languages")} className="flex flex-wrap justify-center gap-x-4 gap-y-1">
          {LANGUAGES.map((code) => (
            <a
              key={code}
              href={`/${code}`}
              hrefLang={code}
              lang={code}
              className="inline-flex min-h-11 items-center text-md text-muted-foreground underline-offset-2 hover:text-foreground hover:underline md:min-h-0"
            >
              {LANGUAGE_NAMES[code]}
            </a>
          ))}
        </nav>
      </footer>
    </div>
  );
}
