import { useState, type ReactNode } from "react";
import { observer } from "mobx-react-lite";
import { Check, ChevronLeft, ReceiptText, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button, Input, PalettePicker } from "@/shared/components";
import { SUPPORTED_CURRENCIES } from "@/config/currencies";
import { LANGUAGES, LANGUAGE_NAMES, type Language } from "@/i18n/languages";
import { useStores } from "@/stores/StoreContext";
import { numberFormat } from "@/i18n/format";
import { RegularIncomes } from "@/features/profile/components/RegularIncomes";
import { guessCurrency } from "./guess";

const STEPS = 6;

/** A decimal string the API takes, or null for an empty field. */
function amountOf(text: string): string | null {
  const value = text.trim().replace(",", ".").replace(/\s/g, "");
  return /^\d+(\.\d{1,2})?$/.test(value) ? value : null;
}

/**
 * The first sign-in (F23.9, docs/design/screens/v2/onboarding-*): language and currency
 * guessed from the browser, the palette — painted as it is picked — the regular incomes
 * (F23.17) and what is on the accounts today, and two-factor sign-in now or later. Skipping
 * at any step keeps the defaults; either way it is not shown again, on any device.
 */
export const OnboardingPage = observer(function OnboardingPage() {
  const { authStore, languageStore, themeStore, profileStore, incomeStore } = useStores();
  const { t } = useTranslation("onboarding");
  const { t: profile } = useTranslation("profile");
  const navigate = useNavigate();
  const user = authStore.user;
  const [step, setStep] = useState(0);
  const [currency, setCurrency] = useState(() =>
    user && user.currency !== "USD"
      ? user.currency
      : guessCurrency(Intl.DateTimeFormat().resolvedOptions().timeZone, navigator.language),
  );
  const [balance, setBalance] = useState("");
  const [twoFactor, setTwoFactor] = useState<"now" | "later">("later");
  const [busy, setBusy] = useState(false);

  const today = new Date();
  const isoToday = `${String(today.getFullYear())}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  const finish = async (to: string, withChoices = true) => {
    setBusy(true);
    const balanceAmount = amountOf(balance);
    const done = await profileStore.finishOnboarding(
      withChoices
        ? {
            currency,
            palette: themeStore.palette,
            ...(balanceAmount ? { starting_balance: balanceAmount, balance_since: isoToday } : {}),
          }
        : {},
    );
    setBusy(false);
    if (done) void navigate(to, { replace: true });
  };

  const choice = (selected: boolean) =>
    `min-h-13 rounded-control border-2 bg-surface px-2 text-lg font-bold ${
      selected ? "border-primary" : "border-border"
    }`;

  return (
    <div className="fixed inset-0 z-30 flex flex-col overflow-y-auto bg-muted text-foreground">
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col px-5 pt-5 pb-8">
        <div className="flex min-h-11 items-center justify-between">
          {step > 0 && step < STEPS - 1 ? (
            <button
              type="button"
              aria-label={t("back")}
              onClick={() => {
                setStep((s) => s - 1);
              }}
              className="flex h-11 w-11 items-center justify-center rounded-pill bg-surface"
            >
              <ChevronLeft size={20} aria-hidden="true" />
            </button>
          ) : (
            <span className="w-11" />
          )}
          <span
            className="flex gap-1.5"
            role="progressbar"
            aria-valuemin={1}
            aria-valuemax={STEPS}
            aria-valuenow={step + 1}
            aria-label={t("steps", { step: step + 1, total: STEPS })}
          >
            {Array.from({ length: STEPS }, (_, i) => (
              <span
                key={i}
                className={`h-1.5 rounded-pill transition-all ${i === step ? "w-6" : "w-1.5"} ${
                  i <= step ? "bg-primary" : "bg-border-strong"
                }`}
              />
            ))}
          </span>
          {step > 0 && step < STEPS - 1 ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void finish("/", false)}
              className="min-h-11 px-1 text-lg font-bold text-muted-foreground"
            >
              {t("skip")}
            </button>
          ) : (
            <span className="w-11" />
          )}
        </div>

        <div className="flex flex-1 flex-col gap-6 pt-6">
          {step === 0 && (
            <div className="flex flex-1 flex-col justify-center gap-7">
              <span className="flex h-22 w-22 items-center justify-center rounded-[28px] bg-primary text-primary-foreground">
                <ReceiptText size={44} aria-hidden="true" />
              </span>
              <Heading title={t("welcome.title")} body={t("welcome.body")} big />
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                {[t("welcome.perk1"), t("welcome.perk2"), t("welcome.perk3")].map((perk) => (
                  <li
                    key={perk}
                    className="rounded-pill bg-tone-primary-bg px-3 py-2 text-md font-bold"
                  >
                    {perk}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {step === 1 && (
            <>
              <Heading title={t("money.title")} body={t("money.body")} />
              <Choices label={t("money.language")}>
                <div className="grid grid-cols-3 gap-2">
                  {LANGUAGES.map((language: Language) => (
                    <button
                      key={language}
                      type="button"
                      aria-pressed={languageStore.language === language}
                      className={choice(languageStore.language === language)}
                      onClick={() => void languageStore.choose(language)}
                    >
                      {LANGUAGE_NAMES[language]}
                    </button>
                  ))}
                </div>
              </Choices>
              <Choices label={t("money.currency")}>
                <div className="grid grid-cols-3 gap-2 md:grid-cols-5">
                  {SUPPORTED_CURRENCIES.map(({ code }) => (
                    <button
                      key={code}
                      type="button"
                      aria-pressed={currency === code}
                      className={choice(currency === code)}
                      onClick={() => {
                        setCurrency(code);
                      }}
                    >
                      {code}
                    </button>
                  ))}
                </div>
                <p className="m-0 text-md text-muted-foreground">{t("money.nbp")}</p>
              </Choices>
            </>
          )}

          {step === 2 && (
            <>
              <Heading title={t("look.title")} body={t("look.body")} />
              <PalettePicker
                label={t("look.title")}
                value={themeStore.palette}
                onChange={(palette) => {
                  themeStore.setPalette(palette);
                }}
              />
            </>
          )}

          {step === 3 && (
            <>
              <Heading title={t("income.title")} body={t("income.body")} />
              <RegularIncomes currency={currency} />
              <div className="flex flex-col gap-1.5">
                <div className="relative">
                  <Input
                    id="onboarding-balance"
                    label={t("income.balance")}
                    inputMode="decimal"
                    value={balance}
                    onChange={(e) => {
                      setBalance(e.target.value);
                    }}
                    className="pr-16 text-lg font-bold tabular-nums"
                  />
                  <span className="pointer-events-none absolute right-4 bottom-3 text-md font-bold text-muted-foreground">
                    {currency}
                  </span>
                </div>
                <p className="m-0 text-md text-muted-foreground">{t("income.balanceHint")}</p>
              </div>
            </>
          )}

          {step === 4 && (
            <>
              <span className="flex h-18 w-18 items-center justify-center rounded-[24px] bg-tone-primary-bg text-primary">
                <ShieldCheck size={36} aria-hidden="true" />
              </span>
              <Heading title={t("security.title")} body={t("security.body")} />
              <div
                className="flex flex-col gap-2.5"
                role="radiogroup"
                aria-label={t("security.title")}
              >
                {(["now", "later"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    role="radio"
                    aria-checked={twoFactor === option}
                    onClick={() => {
                      setTwoFactor(option);
                    }}
                    className={`flex min-h-18 items-center gap-3.5 rounded-card border-2 bg-surface px-4 text-left ${
                      twoFactor === option ? "border-primary" : "border-border"
                    }`}
                  >
                    <span
                      className={`h-5.5 w-5.5 shrink-0 rounded-pill border-2 ${
                        twoFactor === option ? "border-primary bg-primary" : "border-border-strong"
                      }`}
                    />
                    <span className="flex flex-col">
                      <span className="text-lg font-bold">{t(`security.${option}`)}</span>
                      <span className="text-md text-muted-foreground">
                        {t(`security.${option}Hint`)}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </>
          )}

          {step === 5 && (
            <div className="flex flex-1 flex-col justify-center gap-6">
              <span className="flex h-22 w-22 items-center justify-center rounded-pill bg-primary text-primary-foreground">
                <Check size={44} strokeWidth={2.6} aria-hidden="true" />
              </span>
              <Heading title={t("done.title")} body={t("done.body")} big />
              <dl className="m-0 flex flex-col divide-y divide-border overflow-hidden rounded-card bg-surface">
                {[
                  [t("done.language"), LANGUAGE_NAMES[languageStore.language]],
                  [t("done.currency"), currency],
                  [t("done.palette"), profile(`appearance.palettes.${themeStore.palette}`)],
                  [
                    t("done.income"),
                    incomeStore.regular.length > 0
                      ? `${numberFormat({ maximumFractionDigits: 2 }).format(
                          incomeStore.regular.reduce((sum, r) => sum + Number(r.amount), 0),
                        )} ${currency}`
                      : t("income.none"),
                  ],
                  [t("done.twoFactor"), twoFactor === "now" ? t("done.on") : t("done.off")],
                ].map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3 px-4 py-3.5 text-lg">
                    <dt className="text-muted-foreground">{key}</dt>
                    <dd className="m-0 font-bold">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2 pt-6">
          {step < STEPS - 1 ? (
            <Button
              size="lg"
              className="min-h-14 rounded-[18px] text-lg font-extrabold"
              onClick={() => {
                setStep((s) => s + 1);
              }}
            >
              {step === 0 ? t("welcome.start") : t("next")}
            </Button>
          ) : (
            <>
              <Button
                size="lg"
                className="min-h-14 rounded-[18px] text-lg font-extrabold"
                disabled={busy}
                onClick={() => void finish(twoFactor === "now" ? "/settings#security" : "/upload")}
              >
                {twoFactor === "now" ? t("security.now") : t("done.scan")}
              </Button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void finish("/")}
                className="min-h-11 text-lg font-bold text-muted-foreground"
              >
                {t("done.look")}
              </button>
            </>
          )}
          {step === 0 && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void finish("/", false)}
              className="min-h-11 text-lg font-bold text-muted-foreground"
            >
              {t("welcome.defaults")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

function Heading({ title, body, big = false }: { title: string; body: string; big?: boolean }) {
  return (
    <div className="flex flex-col gap-2">
      <h1
        className={`m-0 font-extrabold tracking-[-0.02em] ${big ? "text-[34px] leading-[1.1]" : "text-3xl"}`}
      >
        {title}
      </h1>
      <p className="m-0 text-lg leading-relaxed text-muted-foreground">{body}</p>
    </div>
  );
}

function Choices({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-md font-bold uppercase tracking-[0.06em] text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}
