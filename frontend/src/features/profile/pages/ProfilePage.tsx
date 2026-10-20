import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import {
  AtSign,
  Briefcase,
  CalendarDays,
  ChartColumn,
  ChevronLeft,
  CircleHelp,
  Coins,
  Gauge,
  Globe,
  House,
  Landmark,
  LogOut,
  Mail,
  Moon,
  Percent,
  Plane,
  ReceiptText,
  Target,
  Users,
  Wallet,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useStores } from "@/stores/StoreContext";
import {
  AmountDialog,
  Button,
  inMonth,
  PalettePicker,
  Pill,
  Select,
  Switch,
} from "@/shared/components";
import { CurrencySelect } from "@/shared/components/CurrencySelect/CurrencySelect";
import { numberFormat } from "@/i18n/format";
import { LANGUAGE_NAMES } from "@/i18n/languages";
import { InstallAppCard } from "@/features/install/InstallAppCard";
import { ChangeEmailDialog } from "../components/ChangeEmailDialog";
import { DataCard } from "../components/DataCard";
import { ForwardingAddressCard } from "../components/ForwardingAddressCard";
import { RegularIncomes } from "../components/RegularIncomes";
import { HouseholdCard } from "../components/HouseholdCard";
import { LanguageCard } from "../components/LanguageCard";
import { ReadingAccuracyCard } from "../components/ReadingAccuracyCard";
import { ReceiptUsageCard } from "../components/ReceiptUsageCard";
import { SecurityCard } from "../components/SecurityCard";
import { SettingsGroup, SettingsRow, SettingsSheet } from "../components/SettingsRows";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });

type Sheet =
  | "currency"
  | "budget"
  | "income"
  | "payday"
  | "balance"
  | "regular"
  | "bills"
  | "taxRate"
  | "taxFixed"
  | "language"
  | "forwarding"
  | "usage"
  | "household"
  | "email"
  | null;

/**
 * Settings (F23.8, design v2; was Preferences): who the account is, then grouped rows —
 * appearance, money, language, receipts, sharing and work, the account and its security,
 * the user's data, help — each opening a small dialog of its own, so nothing is a form
 * wrapped in another.
 */
/** A regular income's or bill's sum in this month: a weekly one as often as it falls. */
function monthOf(rule: { amount: string; day?: number | null; weekday?: number | null }): number {
  return inMonth(rule.amount, { day: rule.day ?? null, weekday: rule.weekday ?? null }, new Date());
}

export const ProfilePage = observer(function ProfilePage() {
  const { authStore, profileStore, quotaStore, themeStore, languageStore, incomeStore } =
    useStores();
  const { t } = useTranslation("profile");
  const { t: common } = useTranslation();
  const navigate = useNavigate();
  const [sheet, setSheet] = useState<Sheet>(null);
  const [currency, setCurrency] = useState("");
  const [payday, setPayday] = useState("");
  const user = authStore.user;
  const money = user?.currency ?? "PLN";
  const close = () => {
    setSheet(null);
  };

  useEffect(() => {
    void profileStore.loadProfile();
    void quotaStore.load();
    void incomeStore.loadRegular();
    void incomeStore.loadBills();
  }, [profileStore, quotaStore, incomeStore]);

  const initials =
    `${user?.first_name.charAt(0) ?? ""}${user?.last_name.charAt(0) ?? ""}`.toUpperCase() || "?";
  const quota = quotaStore.quota;
  const amount = (value: string | null | undefined) =>
    value == null ? t("money.none") : `${WHOLE.format(Number(value))} ${money}`;
  const today = new Date();
  const isoToday = `${String(today.getFullYear())}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-5 pb-4">
      <header className="flex items-center gap-3">
        <Link
          to="/"
          aria-label={t("back")}
          className="flex h-11 w-11 items-center justify-center rounded-pill bg-surface text-foreground md:hidden"
        >
          <ChevronLeft size={20} aria-hidden="true" />
        </Link>
        <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em]">{t("title")}</h1>
      </header>

      <section className="flex items-center gap-3.5 rounded-card bg-surface p-4">
        <span
          aria-hidden="true"
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-pill bg-primary text-xl font-extrabold text-primary-foreground"
        >
          {initials}
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="text-lg font-extrabold">
            {user?.first_name} {user?.last_name}
          </span>
          <span className="truncate text-md text-muted-foreground">{user?.email}</span>
          {quota && (
            <span className="mt-1 self-start">
              <Pill tone={quota.plan === "paid" ? "success" : "default"} size="sm">
                {quota.plan === "paid" ? t("usage.planPaid") : t("usage.planFree")}
                {quota.limit !== null && ` · ${String(quota.used)}/${String(quota.limit)}`}
              </Pill>
            </span>
          )}
        </span>
      </section>

      <section className="flex flex-col gap-2.5">
        <h2 className="m-0 px-1 text-md font-bold uppercase tracking-[0.06em] text-muted-foreground">
          {t("appearance.title")}
        </h2>
        <div className="flex flex-col gap-2 rounded-card bg-surface p-4">
          <PalettePicker
            label={t("appearance.palette")}
            value={themeStore.palette}
            onChange={(palette) => {
              void profileStore.choosePalette(palette);
            }}
          />
          <div className="flex items-center gap-3 pt-1">
            <Moon size={18} className="shrink-0 text-muted-foreground" aria-hidden="true" />
            <div className="flex-1">
              <Switch
                checked={themeStore.darkAtNight}
                onChange={(on) => {
                  void profileStore.chooseDarkAtNight(on);
                }}
                label={t("appearance.darkAtNight")}
                hint={t("appearance.darkAtNightHint")}
              />
            </div>
          </div>
        </div>
      </section>

      <SettingsGroup label={t("money.title")}>
        <SettingsRow
          icon={Coins}
          color="var(--cat-utilities)"
          label={t("money.currency")}
          value={money}
          onClick={() => {
            setCurrency(money);
            setSheet("currency");
          }}
        />
        <SettingsRow
          icon={Target}
          label={t("money.limit")}
          value={amount(user?.budget_limit)}
          onClick={() => {
            setSheet("budget");
          }}
        />
        <SettingsRow
          icon={Wallet}
          color="var(--cat-dining)"
          label={t("regular.title")}
          value={
            incomeStore.regular.length === 0
              ? t("regular.none")
              : t("regular.summary", {
                  count: incomeStore.regular.length,
                  amount: amount(
                    String(incomeStore.regular.reduce((sum, r) => sum + monthOf(r), 0)),
                  ),
                })
          }
          onClick={() => {
            setSheet("regular");
          }}
        />
        <SettingsRow
          icon={House}
          color="var(--cat-utilities)"
          label={t("bills.title")}
          value={
            incomeStore.bills.length === 0
              ? t("bills.none")
              : t("bills.summary", {
                  count: incomeStore.bills.length,
                  amount: amount(String(incomeStore.bills.reduce((sum, b) => sum + monthOf(b), 0))),
                })
          }
          onClick={() => {
            setSheet("bills");
          }}
        />
        {/* The single usual income came before regular incomes; kept while it is all there is. */}
        {incomeStore.regular.length === 0 && user?.usual_income != null && (
          <SettingsRow
            icon={Wallet}
            color="var(--cat-dining)"
            label={t("money.income")}
            value={amount(user.usual_income)}
            onClick={() => {
              setSheet("income");
            }}
          />
        )}
        <SettingsRow
          icon={CalendarDays}
          color="var(--cat-transport)"
          label={t("money.payday")}
          value={
            user?.payday == null
              ? t("money.noPayday")
              : user.payday === 31
                ? t("money.lastDay")
                : String(user.payday)
          }
          onClick={() => {
            setPayday(user?.payday == null ? "" : String(user.payday));
            setSheet("payday");
          }}
        />
        <SettingsRow
          icon={Landmark}
          color="var(--cat-health)"
          label={t("money.balance")}
          value={amount(user?.starting_balance)}
          onClick={() => {
            setSheet("balance");
          }}
        />
        <SettingsRow
          icon={ReceiptText}
          color="var(--cat-utilities)"
          label={t("money.taxes")}
          hint={t("money.taxesHint")}
          aside={
            <span className="w-14 shrink-0">
              <Switch
                checked={user?.pays_own_taxes === true}
                onChange={(value) => {
                  void profileStore.saveQuietly({ pays_own_taxes: value });
                }}
                label=""
                ariaLabel={t("money.taxes")}
              />
            </span>
          }
        />
        {user?.pays_own_taxes === true && (
          <>
            <SettingsRow
              icon={Percent}
              color="var(--cat-utilities)"
              label={t("money.taxRate")}
              value={
                user.tax_rate == null
                  ? t("money.none")
                  : t("money.percent", { value: Number(user.tax_rate) })
              }
              onClick={() => {
                setSheet("taxRate");
              }}
            />
            <SettingsRow
              icon={CalendarDays}
              color="var(--cat-utilities)"
              label={t("money.taxFixed")}
              value={amount(user.tax_fixed_monthly)}
              onClick={() => {
                setSheet("taxFixed");
              }}
            />
          </>
        )}
      </SettingsGroup>

      <SettingsGroup label={common("language.label")}>
        <SettingsRow
          icon={Globe}
          color="var(--cat-transport)"
          label={common("language.label")}
          value={LANGUAGE_NAMES[languageStore.language]}
          onClick={() => {
            setSheet("language");
          }}
        />
      </SettingsGroup>

      <SettingsGroup label={t("receiptsGroup")}>
        <SettingsRow
          icon={Mail}
          color="var(--cat-dining)"
          label={t("forwarding.title")}
          hint={user?.forwarding_address}
          onClick={() => {
            setSheet("forwarding");
          }}
        />
        <SettingsRow
          icon={Gauge}
          label={t("usage.title")}
          value={
            quota?.limit != null ? `${String(quota.used)} / ${String(quota.limit)}` : undefined
          }
          onClick={() => {
            setSheet("usage");
          }}
        />
      </SettingsGroup>

      <SettingsGroup label={t("sharing")}>
        <SettingsRow
          icon={Users}
          color="var(--cat-entertainment)"
          label={t("household")}
          onClick={() => {
            setSheet("household");
          }}
        />
        <SettingsRow
          icon={Briefcase}
          color="var(--cat-dining)"
          label={t("work.label")}
          hint={t("work.hint")}
          aside={
            <span className="w-14 shrink-0">
              <Switch
                checked={user?.travels_for_work === true}
                onChange={(value) => {
                  void profileStore.saveQuietly({ travels_for_work: value });
                }}
                label=""
                ariaLabel={t("work.label")}
              />
            </span>
          }
        />
        {user?.travels_for_work === true && (
          <SettingsRow
            icon={Plane}
            color="var(--cat-dining)"
            label={t("work.open")}
            to="/trips?kind=business"
          />
        )}
      </SettingsGroup>

      <SettingsGroup label={t("account.title")}>
        <SettingsRow
          icon={AtSign}
          color="var(--cat-transport)"
          label={t("account.email")}
          value={user?.email_confirmed === false ? t("account.unconfirmed") : t("account.change")}
          onClick={() => {
            setSheet("email");
          }}
        />
        <SecurityCard />
        <SettingsRow
          icon={LogOut}
          color="var(--cat-utilities)"
          label={t("account.signOutEverywhere")}
          hint={t("account.sessionsHint")}
          onClick={() => {
            void authStore.logout();
          }}
        />
      </SettingsGroup>

      <SettingsGroup label={t("data.title")}>
        <DataCard />
      </SettingsGroup>

      <SettingsGroup label={t("more")}>
        <SettingsRow icon={CircleHelp} color="var(--cat-other)" label={t("help")} to="/help" />
        {user?.is_admin === true && (
          <SettingsRow icon={ChartColumn} color="var(--cat-other)" label={t("admin")} to="/admin" />
        )}
        <SettingsRow
          icon={LogOut}
          danger
          label={t("logOut")}
          onClick={() => {
            void authStore.logout().then(() => navigate("/login"));
          }}
        />
      </SettingsGroup>

      <InstallAppCard />

      {sheet === "currency" && (
        <SettingsSheet title={t("money.currency")} onClose={close}>
          <p className="m-0 text-md text-muted-foreground">{t("money.currencyHint")}</p>
          <CurrencySelect
            id="currency"
            aria-label={t("money.currency")}
            value={currency}
            onChange={(e) => {
              setCurrency(e.target.value);
            }}
          />
          <Button
            onClick={() => {
              void profileStore.updateProfile({ currency }).then((ok) => {
                if (ok) close();
              });
            }}
          >
            {t("save")}
          </Button>
        </SettingsSheet>
      )}
      {sheet === "payday" && (
        <SettingsSheet title={t("money.payday")} onClose={close}>
          <p className="m-0 text-md text-muted-foreground">{t("money.hint")}</p>
          <Select
            id="payday"
            aria-label={t("money.payday")}
            value={payday}
            onChange={(e) => {
              setPayday(e.target.value);
            }}
          >
            <option value="">{t("money.noPayday")}</option>
            {Array.from({ length: 30 }, (_, i) => i + 1).map((day) => (
              <option key={day} value={day}>
                {day}
              </option>
            ))}
            <option value="31">{t("money.lastDay")}</option>
          </Select>
          <Button
            onClick={() => {
              void profileStore
                .saveQuietly({ payday: payday ? Number(payday) : null })
                .then((ok) => {
                  if (ok) close();
                });
            }}
          >
            {t("save")}
          </Button>
        </SettingsSheet>
      )}
      {sheet === "budget" && (
        <AmountDialog
          title={t("money.limit")}
          label={t("money.limit")}
          hint={t("money.limitHint")}
          initial={user?.budget_limit ?? ""}
          currency={money}
          allowEmpty
          onSave={(value) =>
            profileStore.saveQuietly({ budget_limit: value === "" ? null : value })
          }
          onClose={close}
        />
      )}
      {sheet === "income" && (
        <AmountDialog
          title={t("money.income")}
          label={t("money.income")}
          hint={t("money.hint")}
          initial={user?.usual_income ?? ""}
          currency={money}
          allowEmpty
          onSave={(value) =>
            profileStore.saveQuietly({ usual_income: value === "" ? null : value })
          }
          onClose={close}
        />
      )}
      {sheet === "balance" && (
        <AmountDialog
          title={t("money.balance")}
          label={t("money.balanceLabel")}
          hint={t("money.balanceHint")}
          initial={incomeStore.balance?.balance ?? ""}
          currency={money}
          onSave={(value) =>
            profileStore.saveQuietly({ starting_balance: value, balance_since: isoToday })
          }
          onClose={close}
        />
      )}
      {sheet === "regular" && (
        <SettingsSheet title={t("regular.title")} onClose={close}>
          <p className="m-0 text-md text-muted-foreground">{t("regular.hint")}</p>
          <RegularIncomes />
        </SettingsSheet>
      )}
      {sheet === "bills" && (
        <SettingsSheet title={t("bills.title")} onClose={close}>
          <p className="m-0 text-md text-muted-foreground">{t("bills.hint")}</p>
          <RegularIncomes kind="bill" />
        </SettingsSheet>
      )}
      {sheet === "taxRate" && (
        <AmountDialog
          title={t("money.taxRate")}
          label={t("money.taxRate")}
          hint={t("money.taxRateHint")}
          initial={user?.tax_rate ?? ""}
          currency="%"
          allowEmpty
          onSave={(value) => profileStore.saveQuietly({ tax_rate: value === "" ? null : value })}
          onClose={close}
        />
      )}
      {sheet === "taxFixed" && (
        <AmountDialog
          title={t("money.taxFixed")}
          label={t("money.taxFixed")}
          hint={t("money.taxFixedHint")}
          initial={user?.tax_fixed_monthly ?? ""}
          currency={money}
          allowEmpty
          onSave={(value) =>
            profileStore.saveQuietly({ tax_fixed_monthly: value === "" ? null : value })
          }
          onClose={close}
        />
      )}
      {sheet === "language" && (
        <SettingsSheet title={common("language.label")} onClose={close}>
          <LanguageCard />
        </SettingsSheet>
      )}
      {sheet === "forwarding" && (
        <SettingsSheet title={t("forwarding.title")} onClose={close}>
          <ForwardingAddressCard />
        </SettingsSheet>
      )}
      {sheet === "usage" && (
        <SettingsSheet title={t("usage.title")} onClose={close}>
          <ReceiptUsageCard />
          <ReadingAccuracyCard />
        </SettingsSheet>
      )}
      {sheet === "household" && (
        <SettingsSheet title={t("household")} onClose={close}>
          <HouseholdCard />
        </SettingsSheet>
      )}
      {sheet === "email" && <ChangeEmailDialog onClose={close} />}
    </div>
  );
});
