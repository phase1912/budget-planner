import { useEffect, useState } from "react";
import {
  ChevronRight,
  Plane,
  PieChart,
  ReceiptText,
  Search,
  ShieldCheck,
  Tags,
  Target,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Input, PublicLinks } from "@/shared/components";
import { ContactForm } from "./ContactForm";

/** The areas of the Help page, their icons and their questions, in the order they are shown. */
const AREAS = {
  receipts: {
    icon: ReceiptText,
    items: ["photo", "long", "email", "total", "manual", "limit", "foreign"],
  },
  spending: { icon: PieChart, items: ["where", "category", "family"] },
  products: { icon: Tags, items: ["cheaper", "rename", "sets"] },
  income: { icon: Wallet, items: ["salary", "taxes", "bills", "balance"] },
  goals: { icon: Target, items: ["kinds", "advice"] },
  household: { icon: Users, items: ["share", "private"] },
  trips: { icon: Plane, items: ["holiday", "business", "perdiem"] },
  account: {
    icon: ShieldCheck,
    items: ["confirm", "password", "install", "export", "photos", "delete"],
  },
} satisfies Record<string, { icon: LucideIcon; items: string[] }>;
type Area = keyof typeof AREAS;
const AREA_KEYS = Object.keys(AREAS) as Area[];

const STEPS = ["add", "check", "see", "plan"] as const;
type Step = (typeof STEPS)[number];

/** A colour per area, from the category palette, so a topic and its answers match. */
const COLOURS = [
  "var(--cat-groceries)",
  "var(--cat-dining)",
  "var(--cat-utilities)",
  "var(--cat-transport)",
  "var(--cat-health)",
  "var(--cat-entertainment)",
  "var(--cat-kids)",
  "var(--cat-pet)",
];

interface Answer {
  area: Area;
  item: string;
  q: string;
  a: string;
  where: string;
}

/**
 * How the app works and the usual questions (F17.10, F17.11): the app in four steps, a
 * search, topics that narrow the answers, each answer saying where in the app the thing is,
 * and a way to write when nothing helps. Public and prerendered with every answer in the
 * page; each has its own address (`/help#trips-perdiem`), which opens it.
 */
export function HelpPage() {
  const { t } = useTranslation("help");
  const { hash } = useLocation();
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState<Area | null>(null);
  const [step, setStep] = useState<Step>("add");

  // The router does not scroll to an anchor by itself: an answer linked to opens at it.
  useEffect(() => {
    if (!hash) return;
    const target = document.getElementById(hash.slice(1));
    if (target instanceof HTMLDetailsElement) target.open = true;
    target?.scrollIntoView();
  }, [hash]);

  const answers: Answer[] = AREA_KEYS.flatMap((area) =>
    AREAS[area].items.map((item) => {
      const key = `areas.${area}.items.${item}` as "areas.receipts.items.photo";
      return { area, item, q: t(`${key}.q`), a: t(`${key}.a`), where: t(`${key}.where`) };
    }),
  );
  const needle = query.trim().toLowerCase();
  const shown = answers.filter(
    (answer) =>
      (!topic || answer.area === topic) &&
      (!needle || `${answer.q} ${answer.a} ${answer.where}`.toLowerCase().includes(needle)),
  );
  const filtered = Boolean(needle || topic);
  const how = t(`steps.${step}.how`, { returnObjects: true });

  return (
    <article className="mx-auto flex w-full max-w-4xl flex-col gap-8 py-6 md:py-10">
      <header className="flex flex-col gap-3">
        <h1 className="m-0 text-4xl font-extrabold tracking-[-0.03em] md:text-5xl">
          {t("heading")}
        </h1>
        <p className="m-0 text-lg leading-relaxed text-muted-foreground">{t("intro")}</p>
        <div className="relative">
          <Search
            size={20}
            aria-hidden="true"
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            type="search"
            aria-label={t("search")}
            placeholder={t("searchPlaceholder")}
            className="min-h-14 w-full pl-12 text-lg"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
          />
        </div>
      </header>

      <section
        aria-labelledby="help-steps"
        className="flex flex-col gap-4 rounded-hero bg-surface p-5 md:p-6"
      >
        <h2 id="help-steps" className="m-0 text-2xl font-extrabold">
          {t("steps.title")}
        </h2>
        <div
          role="tablist"
          aria-label={t("steps.label")}
          className="grid grid-cols-2 gap-2 md:grid-cols-4"
        >
          {STEPS.map((name, i) => (
            <button
              key={name}
              type="button"
              role="tab"
              id={`help-step-${name}`}
              aria-selected={step === name}
              aria-controls="help-step-panel"
              onClick={() => {
                setStep(name);
              }}
              className={`flex min-h-14 items-center gap-2.5 rounded-card border-2 px-3 py-2 text-left text-md font-extrabold ${
                step === name
                  ? "border-primary bg-tone-primary-bg"
                  : "border-transparent bg-background"
              }`}
            >
              <span
                aria-hidden="true"
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-control ${
                  step === name
                    ? "bg-primary text-primary-foreground"
                    : "bg-surface text-muted-foreground"
                }`}
              >
                {i + 1}
              </span>
              {t(`steps.${name}.title`)}
            </button>
          ))}
        </div>
        <div
          id="help-step-panel"
          role="tabpanel"
          aria-labelledby={`help-step-${step}`}
          className="flex flex-col gap-2"
        >
          <h3 className="m-0 text-xl font-extrabold">{t(`steps.${step}.title`)}</h3>
          <ol className="m-0 flex flex-col gap-2 pl-5 text-lg leading-relaxed">
            {how.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="help-topics" className="flex flex-col gap-3">
        <h2 id="help-topics" className="m-0 text-2xl font-extrabold">
          {t("topics")}
        </h2>
        <ul className="m-0 grid list-none grid-cols-2 gap-2 p-0 md:grid-cols-4">
          {AREA_KEYS.map((area, i) => {
            const Icon = AREAS[area].icon;
            const colour = COLOURS[i] ?? "var(--cat-other)";
            const on = topic === area;
            return (
              <li key={area}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => {
                    setTopic(on ? null : area);
                  }}
                  className={`flex min-h-20 w-full flex-col items-start gap-1.5 rounded-card border-2 bg-surface px-3.5 py-3 text-left ${
                    on ? "border-primary" : "border-transparent"
                  }`}
                >
                  <span className="flex items-center gap-2 text-md font-extrabold">
                    <span
                      aria-hidden="true"
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control"
                      style={{
                        color: colour,
                        background: `color-mix(in srgb, ${colour} 16%, transparent)`,
                      }}
                    >
                      <Icon size={17} />
                    </span>
                    {t(`areas.${area}.title`)}
                  </span>
                  <span className="text-sm font-semibold text-muted-foreground">
                    {t("answers.count", { count: AREAS[area].items.length })}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="help-answers" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="help-answers" className="m-0 text-2xl font-extrabold">
            {needle
              ? t("answers.for", { query: query.trim() })
              : topic
                ? t(`areas.${topic}.title`)
                : t("answers.common")}
          </h2>
          {filtered && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setTopic(null);
              }}
              className="min-h-11 px-2 font-extrabold text-primary"
            >
              {t("answers.all")}
            </button>
          )}
        </div>
        {shown.length === 0 ? (
          <p className="m-0 rounded-card bg-surface p-5 text-lg text-muted-foreground">
            {t("answers.none", { query: query.trim() })}
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {shown.map((answer) => (
              <details
                key={`${answer.area}-${answer.item}`}
                id={`${answer.area}-${answer.item}`}
                className="group scroll-mt-4 rounded-card bg-surface"
              >
                <summary className="flex min-h-14 cursor-pointer list-none items-center gap-3 px-4 py-3 [&::-webkit-details-marker]:hidden">
                  <span
                    aria-hidden="true"
                    className="h-2 w-2 shrink-0 rounded-pill"
                    style={{ background: COLOURS[AREA_KEYS.indexOf(answer.area)] }}
                  />
                  <h3 className="m-0 min-w-0 flex-1 text-lg font-extrabold">{answer.q}</h3>
                  <ChevronRight
                    size={18}
                    aria-hidden="true"
                    className="shrink-0 text-muted-foreground transition-transform group-open:rotate-90"
                  />
                </summary>
                <div className="flex flex-col gap-2.5 px-4 pb-4 md:pl-9">
                  <p className="m-0 text-md leading-relaxed text-muted-foreground">{answer.a}</p>
                  <p className="m-0 flex flex-wrap items-center gap-1.5 text-sm font-bold">
                    <span className="text-muted-foreground">{t("answers.where")}</span>
                    <span className="rounded-control bg-background px-2.5 py-1">
                      {answer.where}
                    </span>
                    <a
                      href={`#${answer.area}-${answer.item}`}
                      className="ml-auto inline-flex min-h-11 items-center px-1 text-primary md:min-h-0"
                      aria-label={answer.q}
                    >
                      #
                    </a>
                  </p>
                </div>
              </details>
            ))}
          </div>
        )}
      </section>

      <ContactForm />
      <footer className="border-t border-border pt-6">
        <PublicLinks />
      </footer>
    </article>
  );
}
