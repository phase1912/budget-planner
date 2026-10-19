import { useEffect, useState } from "react";
import {
  Check,
  Plane,
  Plus,
  ReceiptText,
  ShieldCheck,
  Tags,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { LANGUAGES, LANGUAGE_NAMES, type Language } from "@/i18n/languages";
import { PublicLinks, Ring, SegmentedControl } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { PhoneScreen, type PhoneRow } from "../components/PhoneScreen";
import { sampleAmount } from "../sampleAmount";

/** A colour per sample row, in the order the rows are written in the locales. */
const SERIES = [
  "var(--cat-groceries)",
  "var(--cat-dining)",
  "var(--cat-utilities)",
  "var(--cat-transport)",
  "var(--cat-health)",
];
const colour = (i: number): string => SERIES[i % SERIES.length] ?? "var(--cat-other)";

/** The four tabs of "see what you can do", each with its sample amounts and colours. */
const SHOWCASE = {
  home: { amounts: [1450, 3000, 1080, 2550], colours: [0, 1, 2, 4] },
  spending: { amounts: [1240, 420, 310, 280], colours: [0, 1, 3, 2] },
  products: { amounts: [3.79, 59.99, 4.49, 2.69], colours: [0, 2, 3, 1] },
  plan: { amounts: [9000, 2620, 420, 1860], colours: [0, 3, 1, 2] },
} as const;
type Tab = keyof typeof SHOWCASE;

const STEPS = ["shoot", "check", "see"] as const;
const FEATURE_ICONS: LucideIcon[] = [ReceiptText, Tags, Wallet, Users, Plane, ShieldCheck];
const VERSUS_AMOUNTS = [6.58, 11.99, 9.99, 29.99];

/** The page's main way in, and the way to the tour below it. */
function Calls({ second }: { second: "see" | "signIn" }) {
  const { t } = useTranslation("landing");
  const button =
    "flex min-h-14 flex-1 basis-56 items-center justify-center rounded-card px-6 text-lg font-extrabold";
  return (
    <div className="flex w-full max-w-lg flex-wrap justify-center gap-3">
      <Link to="/register" className={`${button} bg-primary text-primary-foreground`}>
        {second === "see" ? t("hero.start") : t("final.start")}
      </Link>
      {second === "see" ? (
        <a href="#see" className={`${button} bg-surface text-foreground`}>
          {t("hero.see")}
        </a>
      ) : (
        <Link to="/login" className={`${button} bg-surface text-foreground`}>
          {t("haveOne")}
        </Link>
      )}
    </div>
  );
}

/**
 * What a visitor without a session sees (F17.2, F17.11 — landing variant C): a big promise
 * over three of the app's screens, "one total vs every line", three steps, a tour of Home,
 * Spending, Products and Plan, the features, the free plan, questions and a way in. Tied
 * to no country or currency: sample amounts carry none and shops are generic. At "/" it
 * reads in the visitor's language; at "/en", "/uk" and "/pl" in that one, which is also
 * how it is prerendered for search engines, and opening one chooses its language.
 */
export function PublicLandingPage({ language }: { language?: Language }) {
  const { t } = useTranslation("landing");
  const { languageStore } = useStores();
  const [tab, setTab] = useState<Tab>("home");

  useEffect(() => {
    if (language && languageStore.language !== language) void languageStore.choose(language);
  }, [language, languageStore]);

  const rowsOf = (name: Tab): PhoneRow[] => {
    const text = t(`showcase.${name}.rows`, { returnObjects: true }) as {
      name: string;
      sub: string;
    }[];
    return text.map((row, i) => ({
      ...row,
      amount: SHOWCASE[name].amounts[i] ?? 0,
      color: colour(SHOWCASE[name].colours[i] ?? 0),
    }));
  };
  const homeRows = (
    t("phones.home.rows", { returnObjects: true }) as { name: string; sub: string }[]
  ).map((row, i) => ({ ...row, amount: [7920, 103][i] ?? 0, color: colour(i * 3) }));
  const versus = t("versus.lines", { returnObjects: true }) as { name: string; category: string }[];
  const features = t("features.items", { returnObjects: true }) as {
    title: string;
    text: string;
  }[];
  const faq = t("faq.items", { returnObjects: true }) as { q: string; a: string }[];
  const points = t(`showcase.${tab}.points`, { returnObjects: true });
  const heading = "m-0 text-3xl font-extrabold tracking-[-0.03em] md:text-4xl";

  return (
    <div className="flex w-full flex-grow flex-col items-center gap-16 pb-10 pt-6 md:gap-24 md:pt-12">
      <section
        aria-labelledby="landing-title"
        className="flex w-full max-w-6xl flex-col items-center gap-5 text-center"
      >
        <h1
          id="landing-title"
          className="m-0 max-w-[15ch] text-5xl font-extrabold leading-none tracking-[-0.04em] md:text-7xl"
        >
          {t("hero.title")}
        </h1>
        <p className="m-0 max-w-2xl text-lg leading-relaxed text-muted-foreground text-pretty md:text-xl">
          {t("hero.lead")}
        </p>
        <Calls second="see" />
        <p className="m-0 text-base text-muted-foreground">{t("hero.free")}</p>

        <div className="flex w-full items-end justify-center gap-5 pt-6">
          <figure className="m-0 hidden min-w-0 flex-1 flex-col items-center gap-3 lg:flex lg:-rotate-3 lg:translate-y-8">
            <PhoneScreen title={t("phones.spending.title")} rows={rowsOf("spending")} />
            <figcaption className="text-md font-bold text-muted-foreground">
              {t("phones.spending.caption")}
            </figcaption>
          </figure>
          <figure className="m-0 flex min-w-0 flex-1 flex-col items-center gap-3">
            <PhoneScreen
              title={t("phones.home.title")}
              rows={homeRows}
              top={
                <Ring
                  segments={[{ value: 62, color: "var(--color-primary)" }]}
                  max={100}
                  className="my-1 h-36 w-36 self-center"
                  label={t("phones.home.ring")}
                >
                  <span className="text-xl font-extrabold tabular-nums">{sampleAmount(1450)}</span>
                  <span className="max-w-24 text-xs font-semibold text-muted-foreground">
                    {t("phones.home.ring")}
                  </span>
                </Ring>
              }
            />
            <figcaption className="text-md font-bold text-muted-foreground">
              {t("phones.home.caption")}
            </figcaption>
          </figure>
          <figure className="m-0 hidden min-w-0 flex-1 flex-col items-center gap-3 lg:flex lg:rotate-3 lg:translate-y-8">
            <PhoneScreen title={t("phones.products.title")} rows={rowsOf("products")} />
            <figcaption className="text-md font-bold text-muted-foreground">
              {t("phones.products.caption")}
            </figcaption>
          </figure>
        </div>
      </section>

      <section
        aria-labelledby="landing-versus"
        className="flex w-full max-w-6xl flex-col gap-4 md:flex-row"
      >
        <div className="flex flex-1 flex-col gap-3 rounded-hero bg-surface p-6">
          <span className="text-md font-extrabold uppercase tracking-wider text-muted-foreground">
            {t("versus.others")}
          </span>
          <span className="text-2xl font-extrabold tabular-nums">
            {t("versus.othersShop")} · {sampleAmount(58.55)}
          </span>
          <span className="text-lg leading-relaxed text-muted-foreground">
            {t("versus.othersText")}
          </span>
        </div>
        <div className="flex flex-1 flex-col gap-2.5 rounded-hero bg-tone-primary-bg p-6">
          <h2
            id="landing-versus"
            className="m-0 text-md font-extrabold uppercase tracking-wider text-primary"
          >
            {t("versus.ours")}
          </h2>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {versus.map((line, i) => (
              <li key={line.name} className="flex items-center gap-2.5 text-lg font-bold">
                <span
                  aria-hidden="true"
                  className="h-2.5 w-2.5 shrink-0 rounded-pill"
                  style={{ background: colour([0, 2, 1, 4][i] ?? 0) }}
                />
                <span className="min-w-0 flex-1">{line.name}</span>
                <span className="text-md font-semibold text-muted-foreground">{line.category}</span>
                <span className="tabular-nums">{sampleAmount(VERSUS_AMOUNTS[i] ?? 0)}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="landing-steps" className="flex w-full max-w-6xl flex-col gap-5">
        <h2 id="landing-steps" className={heading}>
          {t("steps.title")}
        </h2>
        <ol className="m-0 grid list-none grid-cols-1 gap-3.5 p-0 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step} className="flex flex-col gap-2.5 rounded-hero bg-surface p-6">
              <span
                aria-hidden="true"
                className="flex h-11 w-11 items-center justify-center rounded-control bg-tone-primary-bg text-lg font-extrabold text-primary"
              >
                {i + 1}
              </span>
              <span className="text-xl font-extrabold">{t(`steps.${step}.title`)}</span>
              <span className="text-md leading-relaxed text-muted-foreground">
                {t(`steps.${step}.text`)}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section
        id="see"
        aria-labelledby="landing-see"
        className="flex w-full max-w-6xl scroll-mt-20 flex-col gap-5 rounded-hero bg-surface p-5 md:p-8"
      >
        <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
          <h2 id="landing-see" className={heading}>
            {t("showcase.title")}
          </h2>
          <span className="text-md text-muted-foreground">{t("showcase.note")}</span>
        </div>
        <div className="on-surface">
          <SegmentedControl<Tab>
            label={t("showcase.title")}
            fill
            value={tab}
            onChange={setTab}
            options={(Object.keys(SHOWCASE) as Tab[]).map((name) => ({
              value: name,
              label: t(`showcase.${name}.label`),
            }))}
          />
        </div>
        <div className="flex flex-col items-center gap-8 md:flex-row">
          <div className="flex min-w-0 flex-1 flex-col gap-4">
            <h3 className="m-0 text-2xl font-extrabold tracking-[-0.02em] md:text-3xl">
              {t(`showcase.${tab}.title`)}
            </h3>
            <p className="m-0 text-lg leading-relaxed text-muted-foreground">
              {t(`showcase.${tab}.text`)}
            </p>
            <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
              {points.map((point) => (
                <li key={point} className="flex gap-2.5 text-lg font-bold">
                  <Check size={20} aria-hidden="true" className="mt-0.5 shrink-0 text-primary" />
                  {point}
                </li>
              ))}
            </ul>
          </div>
          <figure className="m-0 flex w-full flex-1 justify-center">
            <PhoneScreen
              title={t(`showcase.${tab}.screen`)}
              rows={rowsOf(tab)}
              className="bg-background"
            />
          </figure>
        </div>
      </section>

      <section aria-labelledby="landing-features" className="flex w-full max-w-6xl flex-col gap-5">
        <h2 id="landing-features" className={heading}>
          {t("features.title")}
        </h2>
        <ul className="m-0 grid list-none grid-cols-1 gap-3.5 p-0 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => {
            const Icon = FEATURE_ICONS[i] ?? Plus;
            const tint = colour(i);
            return (
              <li key={feature.title} className="flex flex-col gap-2.5 rounded-hero bg-surface p-6">
                <span
                  aria-hidden="true"
                  className="flex h-11 w-11 items-center justify-center rounded-control"
                  style={{
                    color: tint,
                    background: `color-mix(in srgb, ${tint} 16%, transparent)`,
                  }}
                >
                  <Icon size={22} />
                </span>
                <h3 className="m-0 text-xl font-extrabold">{feature.title}</h3>
                <p className="m-0 text-md leading-relaxed text-muted-foreground">{feature.text}</p>
              </li>
            );
          })}
        </ul>
      </section>

      <section
        aria-labelledby="landing-free"
        className="flex w-full max-w-6xl flex-col gap-4 rounded-hero bg-tone-primary-bg p-6 md:flex-row md:items-center md:p-9"
      >
        <div className="flex flex-1 flex-col gap-2">
          <h2 id="landing-free" className={heading}>
            {t("free.title")}
          </h2>
          <p className="m-0 text-lg leading-relaxed text-muted-foreground">{t("free.text")}</p>
        </div>
        <p className="m-0 flex items-baseline gap-2.5">
          <span className="text-6xl font-extrabold tracking-[-0.03em] tabular-nums">
            {t("free.amount")}
          </span>
          <span className="text-lg font-bold text-muted-foreground">{t("free.unit")}</span>
        </p>
      </section>

      <section aria-labelledby="landing-faq" className="flex w-full max-w-3xl flex-col gap-4">
        <h2 id="landing-faq" className={heading}>
          {t("faq.title")}
        </h2>
        <div className="flex flex-col gap-2">
          {faq.map((item) => (
            <details key={item.q} className="group rounded-card bg-surface px-4 md:px-5">
              <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 py-3 text-lg font-extrabold [&::-webkit-details-marker]:hidden">
                {item.q}
                <Plus
                  size={20}
                  aria-hidden="true"
                  className="shrink-0 text-primary transition-transform group-open:rotate-45"
                />
              </summary>
              <p className="m-0 pb-4 text-md leading-relaxed text-muted-foreground">{item.a}</p>
            </details>
          ))}
        </div>
        <Link to="/help" className="inline-flex min-h-11 items-center font-extrabold text-primary">
          {t("faq.more")}
        </Link>
      </section>

      <section
        aria-labelledby="landing-final"
        className="flex w-full max-w-6xl flex-col items-center gap-5 text-center"
      >
        <h2
          id="landing-final"
          className="m-0 max-w-[14ch] text-4xl font-extrabold leading-none tracking-[-0.04em] md:text-6xl"
        >
          {t("final.title")}
        </h2>
        <Calls second="signIn" />
      </section>

      <footer className="flex w-full max-w-6xl flex-col items-center gap-2 border-t border-border pt-6 text-center">
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
        <PublicLinks />
      </footer>
    </div>
  );
}
