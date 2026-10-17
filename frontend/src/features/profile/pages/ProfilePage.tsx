import { useState, useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { useStores } from "@/stores/StoreContext";
import { Card, CardHeader, CardBody } from "@/shared/components/Card/Card";
import { Button, Pill } from "@/shared/components";
import { InstallAppCard } from "@/features/install/InstallAppCard";
import { AppearanceCard } from "../components/AppearanceCard";
import { ChangeEmailDialog } from "../components/ChangeEmailDialog";
import { DataCard } from "../components/DataCard";
import { ForwardingAddressCard } from "../components/ForwardingAddressCard";
import { HouseholdCard } from "../components/HouseholdCard";
import { LanguageCard } from "../components/LanguageCard";
import { MoneyCard } from "../components/MoneyCard";
import { ReadingAccuracyCard } from "../components/ReadingAccuracyCard";
import { ReceiptUsageCard } from "../components/ReceiptUsageCard";
import { SecurityCard } from "../components/SecurityCard";
import { WorkTripsCard } from "../components/WorkTripsCard";

/**
 * Settings (F23.8, was Preferences): who the account is, then how the product looks, money,
 * language, receipts by email, the household, work trips, the account and its security,
 * and the user's data — each a card of its own, each saving on its own, so no form wraps
 * another.
 */
export const ProfilePage = observer(function ProfilePage() {
  const { authStore, profileStore, quotaStore, accountStore } = useStores();
  const { t } = useTranslation("profile");
  const [changingEmail, setChangingEmail] = useState(false);
  const user = authStore.user;

  useEffect(() => {
    void profileStore.loadProfile();
    void quotaStore.load();
  }, [profileStore, quotaStore]);

  const initials =
    `${user?.first_name.charAt(0) ?? ""}${user?.last_name.charAt(0) ?? ""}`.toUpperCase() || "?";
  const quota = quotaStore.quota;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 py-4 md:gap-6 md:py-6">
      <h1 className="m-0 text-[24px] font-bold text-foreground md:text-3xl">{t("title")}</h1>

      <section className="flex items-center gap-4 rounded-card bg-surface p-4 shadow-card md:p-5">
        <span
          aria-hidden="true"
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-pill bg-primary text-xl font-bold text-primary-foreground"
        >
          {initials}
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="text-lg font-bold">
            {user?.first_name} {user?.last_name}
          </span>
          <span className="truncate text-md text-muted-foreground">{user?.email}</span>
        </span>
        {quota && (
          <Pill tone={quota.plan === "paid" ? "success" : "default"} size="sm">
            {quota.plan === "paid" ? t("usage.planPaid") : t("usage.planFree")}
          </Pill>
        )}
      </section>

      <AppearanceCard />
      <MoneyCard />
      <LanguageCard />
      <ForwardingAddressCard />
      <ReceiptUsageCard />
      <ReadingAccuracyCard />
      <HouseholdCard />
      <WorkTripsCard />
      <InstallAppCard />

      <Card variant="surface" flush>
        <CardHeader>{t("account.title")}</CardHeader>
        <CardBody className="flex flex-col gap-5.5">
          <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center md:gap-8">
            <div className="flex w-full max-w-md flex-col gap-1">
              <span className="text-lg font-semibold text-foreground">{t("account.email")}</span>
              <span className="break-all text-md text-muted-foreground">{user?.email}</span>
              {accountStore.mustConfirm && (
                <span className="text-base text-tone-warning-text">{t("account.unconfirmed")}</span>
              )}
            </div>
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto"
              onClick={() => {
                accountStore.reset();
                setChangingEmail(true);
              }}
            >
              {t("account.change")}
            </Button>
          </div>
          <div className="h-px bg-border" />
          <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center md:gap-8">
            <div className="flex w-full max-w-md flex-col gap-1">
              <span className="text-lg font-semibold text-foreground">{t("account.sessions")}</span>
              <span className="text-md leading-relaxed text-muted-foreground">
                {t("account.sessionsHint")}
              </span>
            </div>
            <Button
              type="button"
              variant="danger"
              className="w-full md:w-auto"
              onClick={() => {
                void authStore.logout();
              }}
            >
              {t("account.signOutEverywhere")}
            </Button>
          </div>
        </CardBody>
      </Card>

      <SecurityCard />
      <DataCard />
      {changingEmail && (
        <ChangeEmailDialog
          onClose={() => {
            setChangingEmail(false);
          }}
        />
      )}
    </div>
  );
});
