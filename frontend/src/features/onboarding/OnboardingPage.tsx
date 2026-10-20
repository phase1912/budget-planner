import { useEffect, useState, type ReactNode } from "react";
import { observer } from "mobx-react-lite";
import { Check, ChevronLeft, Landmark, ReceiptText, ShieldCheck, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button, Input, PalettePicker, Switch } from "@/shared/components";
import { SUPPORTED_CURRENCIES } from "@/config/currencies";
import { LANGUAGES, LANGUAGE_NAMES, type Language } from "@/i18n/languages";
import { useStores } from "@/stores/StoreContext";
import { numberFormat } from "@/i18n/format";
import { RegularIncomes } from "@/features/profile/components/RegularIncomes";
import { guessCurrency } from "./guess";

const STEPS = 8;
const RATES = ["5", "6", "12"] as const;

/** The steps in order; the family and accounts ones are F12 and F23.15's. */
const WELCOME = 0;
const MONEY = 1;
const LOOK = 2;
const ACCOUNTS = 3;
const INCOME = 4;
const FAMILY = 5;
const SECURITY = 6;
const DONE = 7;

/** A decimal string the API takes, or null for an empty field. */
function amountOf(text: string): string | null {
  const value = text.trim().replace(",", ".").replace(/\s/g, "");
  return /^\d+(\.\d{1,2})?$/.test(value) ? value : null;
}

/**
 * The first sign-in (F23.9, docs/design/screens/v2/onboarding-*): language and currency
 * guessed from the browser, the palette — painted as it is picked — the card purchases are
 * paid from and, for one who runs a business, its account and tax (F23.15), the regular
 * incomes (F23.17), keeping the budget with the family (E12), and two-factor sign-in now
 * or later. Skipping at any step keeps the defaults; either way it is not shown again, on
 * any device.
 */
export const OnboardingPage = observer(function OnboardingPage() {
  const {
    authStore,
    languageStore,
    themeStore,
    profileStore,
    incomeStore,
    bankAccountsStore,
    householdStore,
  } = useStores();
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
  const [cardName, setCardName] = useState("");
  const [cardAmount, setCardAmount] = useState("");
  const [business, setBusiness] = useState(false);
  const [businessAmount, setBusinessAmount] = useState("");
  const [rate, setRate] = useState<string>("5");
  const [ownRate, setOwnRate] = useState("");
  // What this setup already opened, so going back and on again opens nothing twice.
  const [opened, setOpened] = useState<{ card: boolean; business: boolean }>({
    card: false,
    business: false,
  });
  const [together, setTogether] = useState<"alone" | "family">("alone");
  const [familyName, setFamilyName] = useState("");
  const [copied, setCopied] = useState(false);
  const [twoFactor, setTwoFactor] = useState<"now" | "later">("later");
  const [busy, setBusy] = useState(false);

  const today = new Date();
  const isoToday = `${String(today.getFullYear())}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  useEffect(() => {
    if (!householdStore.loaded) void householdStore.load();
    void bankAccountsStore.load(isoToday);
  }, [householdStore, bankAccountsStore, isoToday]);
  // Someone joining a family that already pays from a shared card keeps paying from it.
  const familyCard = bankAccountsStore.accounts.find((a) => a.shared && a.for_purchases);

  const finish = async (to: string, withChoices = true) => {
    setBusy(true);
    const done = await profileStore.finishOnboarding(
      withChoices ? { currency, palette: themeStore.palette } : {},
    );
    setBusy(false);
    if (done) void navigate(to, { replace: true });
  };

  const taxRate = rate === "own" ? amountOf(ownRate) : rate;
  const shared = householdStore.mayShare;
  const invite = householdStore.inviteLink(window.location.origin);

  /** Open the purchase card and, if asked, the business account — once each. */
  const openAccounts = async (): Promise<boolean> => {
    const cardOpening = amountOf(cardAmount);
    const businessOpening = amountOf(businessAmount);
    if (!opened.card && !familyCard && cardOpening !== null) {
      const ok = await bankAccountsStore.open(
        {
          name:
            cardName.trim() ||
            (shared ? t("accounts.cardDefaultShared") : t("accounts.cardDefault")),
          kind: "personal",
          opening: cardOpening,
          opening_on: isoToday,
          tax_rate: null,
          shared,
          for_purchases: true,
        },
        isoToday,
      );
      if (!ok) return false;
      setOpened((o) => ({ ...o, card: true }));
    }
    if (business && !opened.business && businessOpening !== null && taxRate !== null) {
      const ok = await bankAccountsStore.open(
        {
          name: t("accounts.businessDefault"),
          kind: "business",
          opening: businessOpening,
          opening_on: isoToday,
          tax_rate: taxRate,
          shared,
          for_purchases: false,
        },
        isoToday,
      );
      if (!ok) return false;
      setOpened((o) => ({ ...o, business: true }));
    }
    return true;
  };

  const next = async () => {
    if (step === ACCOUNTS) {
      setBusy(true);
      const ok = await openAccounts();
      setBusy(false);
      if (!ok) return;
    }
    // Starting a family stays on its step, to copy the invite link; the next press goes on.
    if (step === FAMILY && together === "family" && !householdStore.household) {
      setBusy(true);
      await householdStore.create(familyName.trim() || t("family.nameDefault"));
      setBusy(false);
      return;
    }
    setStep((s) => s + 1);
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
          {step === WELCOME && (
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

          {step === MONEY && (
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

          {step === LOOK && (
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

          {step === ACCOUNTS && (
            <>
              <span className="flex h-18 w-18 items-center justify-center rounded-[24px] bg-tone-primary-bg text-primary">
                <Landmark size={36} aria-hidden="true" />
              </span>
              <Heading title={t("accounts.title")} body={t("accounts.body")} />
              {familyCard ? (
                <p className="on-surface m-0 rounded-card bg-surface p-4 text-md">
                  {t("accounts.familyCard", { name: familyCard.name })}
                </p>
              ) : (
                <div className="on-surface flex flex-col gap-3 rounded-card bg-surface p-4">
                  <Input
                    label={t("accounts.cardName")}
                    placeholder={
                      shared ? t("accounts.cardDefaultShared") : t("accounts.cardDefault")
                    }
                    maxLength={60}
                    value={cardName}
                    disabled={opened.card}
                    onChange={(e) => {
                      setCardName(e.target.value);
                    }}
                  />
                  <Money
                    id="onboarding-card"
                    label={t("accounts.onIt")}
                    value={cardAmount}
                    currency={currency}
                    disabled={opened.card}
                    onChange={setCardAmount}
                  />
                  <p className="m-0 text-md text-muted-foreground">
                    {shared ? t("accounts.cardHintShared") : t("accounts.cardHint")}
                  </p>
                </div>
              )}
              <div className="on-surface flex flex-col gap-3 rounded-card bg-surface p-4">
                <Switch
                  checked={business}
                  disabled={opened.business}
                  onChange={setBusiness}
                  label={t("accounts.business")}
                  hint={t("accounts.businessHint")}
                />
                {business && (
                  <>
                    <Money
                      id="onboarding-business"
                      label={t("accounts.onIt")}
                      value={businessAmount}
                      currency={currency}
                      disabled={opened.business}
                      onChange={setBusinessAmount}
                    />
                    <Choices label={t("accounts.tax")}>
                      <div className="grid grid-cols-4 gap-2">
                        {[...RATES, "own"].map((r) => (
                          <button
                            key={r}
                            type="button"
                            aria-pressed={rate === r}
                            disabled={opened.business}
                            className={choice(rate === r)}
                            onClick={() => {
                              setRate(r);
                            }}
                          >
                            {r === "own" ? t("accounts.own") : `${r}%`}
                          </button>
                        ))}
                      </div>
                      {rate === "own" && (
                        <Input
                          label={t("accounts.ownRate")}
                          inputMode="decimal"
                          value={ownRate}
                          disabled={opened.business}
                          onChange={(e) => {
                            setOwnRate(e.target.value);
                          }}
                        />
                      )}
                    </Choices>
                  </>
                )}
              </div>
              <p className="m-0 text-md text-muted-foreground">{t("accounts.later")}</p>
            </>
          )}

          {step === INCOME && (
            <>
              <Heading title={t("income.title")} body={t("income.body")} />
              <RegularIncomes currency={currency} />
            </>
          )}

          {step === FAMILY && (
            <>
              <span className="flex h-18 w-18 items-center justify-center rounded-[24px] bg-tone-primary-bg text-primary">
                <Users size={36} aria-hidden="true" />
              </span>
              <Heading title={t("family.title")} body={t("family.body")} />
              {householdStore.household ? (
                <div className="flex flex-col gap-3 rounded-card bg-surface p-4">
                  <span className="text-lg font-bold">
                    {t("family.in", { name: householdStore.household.name })}
                  </span>
                  {invite && (
                    <>
                      <p className="m-0 text-md text-muted-foreground">{t("family.invite")}</p>
                      <output className="break-all rounded-control bg-muted px-3 py-2.5 font-mono text-md">
                        {invite}
                      </output>
                      <Button
                        variant="secondary"
                        className="min-h-11"
                        onClick={() => {
                          void navigator.clipboard.writeText(invite).then(() => {
                            setCopied(true);
                          });
                        }}
                      >
                        {copied ? t("family.copied") : t("family.copy")}
                      </Button>
                    </>
                  )}
                </div>
              ) : (
                <>
                  <div
                    className="flex flex-col gap-2.5"
                    role="radiogroup"
                    aria-label={t("family.title")}
                  >
                    {(["alone", "family"] as const).map((option) => (
                      <Option
                        key={option}
                        selected={together === option}
                        title={t(`family.${option}`)}
                        hint={t(`family.${option}Hint`)}
                        onSelect={() => {
                          setTogether(option);
                        }}
                      />
                    ))}
                  </div>
                  {together === "family" && (
                    <Input
                      label={t("family.name")}
                      placeholder={t("family.nameDefault")}
                      maxLength={60}
                      value={familyName}
                      onChange={(e) => {
                        setFamilyName(e.target.value);
                      }}
                    />
                  )}
                </>
              )}
            </>
          )}

          {step === SECURITY && (
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
                  <Option
                    key={option}
                    selected={twoFactor === option}
                    title={t(`security.${option}`)}
                    hint={t(`security.${option}Hint`)}
                    onSelect={() => {
                      setTwoFactor(option);
                    }}
                  />
                ))}
              </div>
            </>
          )}

          {step === DONE && (
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
                  [
                    t("done.accounts"),
                    bankAccountsStore.accounts.length > 0
                      ? `${String(bankAccountsStore.accounts.length)} · ${numberFormat({ maximumFractionDigits: 0 }).format(Number(bankAccountsStore.total))} ${currency}`
                      : t("income.none"),
                  ],
                  [t("done.family"), householdStore.household?.name ?? t("done.alone")],
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
              disabled={busy}
              onClick={() => void next()}
            >
              {step === WELCOME
                ? t("welcome.start")
                : step === FAMILY && together === "family" && !householdStore.household
                  ? t("family.start")
                  : t("next")}
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
          {step === WELCOME && (
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

function Option({
  selected,
  title,
  hint,
  onSelect,
}: {
  selected: boolean;
  title: string;
  hint: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={`flex min-h-18 items-center gap-3.5 rounded-card border-2 bg-surface px-4 py-3 text-left ${
        selected ? "border-primary" : "border-border"
      }`}
    >
      <span
        className={`h-5.5 w-5.5 shrink-0 rounded-pill border-2 ${
          selected ? "border-primary bg-primary" : "border-border-strong"
        }`}
      />
      <span className="flex flex-col">
        <span className="text-lg font-bold">{title}</span>
        <span className="text-md text-muted-foreground">{hint}</span>
      </span>
    </button>
  );
}

/** An amount field with its currency inside, as the first sign-in asks for money. */
function Money({
  id,
  label,
  value,
  currency,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  currency: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative">
      <Input
        id={id}
        label={label}
        inputMode="decimal"
        value={value}
        disabled={disabled}
        onChange={(e) => {
          onChange(e.target.value);
        }}
        className="pr-16 text-lg font-bold tabular-nums"
      />
      <span className="pointer-events-none absolute right-4 bottom-3 text-md font-bold text-muted-foreground">
        {currency}
      </span>
    </div>
  );
}
