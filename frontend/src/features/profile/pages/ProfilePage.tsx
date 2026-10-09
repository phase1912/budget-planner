import { useState, useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { CurrencySelect } from "@/shared/components/CurrencySelect/CurrencySelect";
import { Card, CardHeader, CardBody } from "@/shared/components/Card/Card";
import { Input } from "@/shared/components/Input/Input";
import { Button } from "@/shared/components/Button/Button";
import { ForwardingAddressCard } from "../components/ForwardingAddressCard";
import { HouseholdCard } from "../components/HouseholdCard";
import { ReceiptUsageCard } from "../components/ReceiptUsageCard";
import { InstallAppCard } from "@/features/install/InstallAppCard";

export const ProfilePage = observer(function ProfilePage() {
  const { authStore, profileStore, quotaStore } = useStores();

  const [currency, setCurrency] = useState("USD");
  const [budgetLimit, setBudgetLimit] = useState("");

  const originalCurrency = authStore.user?.currency ?? "USD";
  const originalBudgetLimit = authStore.user?.budget_limit?.toString() ?? "";

  const isDirty = currency !== originalCurrency || budgetLimit !== originalBudgetLimit;

  useEffect(() => {
    void profileStore.loadProfile();
    void quotaStore.load();
  }, [profileStore, quotaStore]);

  useEffect(() => {
    if (authStore.user) {
      setCurrency(originalCurrency);
      setBudgetLimit(originalBudgetLimit);
    }
  }, [authStore.user, originalCurrency, originalBudgetLimit]);

  const handleSubmit = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (!isDirty) return;
    await profileStore.updateProfile({
      currency,
      budget_limit: budgetLimit.trim() === "" ? null : parseFloat(budgetLimit),
    });
  };

  const handleRemoveLimit = () => {
    setBudgetLimit("");
  };

  // Mock value until E2 is implemented
  // eslint-disable-next-line prefer-const
  let receiptCount = 0;
  const isCurrencyLocked = receiptCount > 0;

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col gap-4 py-4 md:gap-6 md:py-10 md:px-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-bold text-foreground md:text-3xl">Preferences</h1>
        <p className="text-lg text-muted-foreground md:text-xl">
          Account-level settings that every figure in the product is expressed in.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="flex flex-col gap-6"
      >
        <Card variant="surface" flush>
          <CardHeader>Money</CardHeader>
          <CardBody className="flex flex-col gap-5.5">
            <div className="flex flex-col md:flex-row items-start justify-between gap-6 md:gap-8">
              <div className="flex flex-col gap-1 w-full max-w-sm">
                <span className="font-semibold text-lg text-foreground">Currency</span>
                <span className="text-md leading-relaxed text-muted-foreground">
                  Locked once a receipt exists &mdash; the product records one currency per account
                  and does not convert between them.
                </span>
              </div>
              <div className="w-full md:w-64 flex-shrink-0 flex flex-col gap-2">
                {isCurrencyLocked ? (
                  <Input value={`${currency} — Locked`} disabled aria-label="Currency" />
                ) : (
                  <CurrencySelect
                    id="currency"
                    value={currency}
                    onChange={(e) => {
                      setCurrency(e.target.value);
                    }}
                    aria-label="Currency"
                    required
                  />
                )}
                {isCurrencyLocked && (
                  <span className="text-sm text-muted-foreground">
                    {receiptCount} receipts recorded in {currency}
                  </span>
                )}
              </div>
            </div>

            <div className="h-px bg-border" />

            <div className="flex flex-col md:flex-row items-start justify-between gap-6 md:gap-8">
              <div className="flex flex-col gap-1 w-full max-w-sm">
                <span className="font-semibold text-lg text-foreground">Monthly budget limit</span>
                <span className="text-md leading-relaxed text-muted-foreground">
                  Optional. When set, spend is also shown as a percentage of it. Changing it affects
                  presentation only &mdash; finalised months are never rewritten.
                </span>
              </div>
              <div className="w-full md:w-64 flex-shrink-0 flex flex-col gap-2">
                <div className="relative flex items-center">
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={budgetLimit}
                    onChange={(e) => {
                      setBudgetLimit(e.target.value);
                    }}
                    aria-label="Monthly budget limit"
                    containerClassName="w-full"
                    className="pr-12 w-full"
                  />
                  <span className="absolute right-3 text-lg text-muted-foreground pointer-events-none">
                    {currency}
                  </span>
                </div>
                {budgetLimit && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="compact"
                    className="self-start p-0 h-auto text-md underline text-muted-foreground hover:bg-transparent hover:text-foreground"
                    onClick={handleRemoveLimit}
                  >
                    Remove the limit
                  </Button>
                )}
              </div>
            </div>
          </CardBody>
        </Card>

        <ReceiptUsageCard />

        <ForwardingAddressCard />

        <HouseholdCard />

        <InstallAppCard />

        <Card variant="surface" flush>
          <CardHeader>Account</CardHeader>
          <CardBody className="flex flex-col gap-5.5">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 md:gap-8">
              <div className="flex flex-col gap-1 w-full max-w-md">
                <span className="font-semibold text-lg text-foreground">Email</span>
                <span className="text-md text-muted-foreground">{authStore.user?.email}</span>
              </div>
              <Button type="button" variant="secondary" disabled className="w-full md:w-auto">
                Change
              </Button>
            </div>

            <div className="h-px bg-border" />

            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 md:gap-8">
              <div className="flex flex-col gap-1 w-full max-w-md">
                <span className="font-semibold text-lg text-foreground">Active sessions</span>
                <span className="text-md leading-relaxed text-muted-foreground">
                  Signing out everywhere revokes every refresh token, including this one.
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
                Sign out everywhere
              </Button>
            </div>
          </CardBody>
        </Card>

        <div className="flex flex-col-reverse gap-2 md:flex-row md:items-center md:justify-end md:gap-3">
          <Button
            type="button"
            variant="ghost"
            disabled={!isDirty}
            onClick={() => {
              setCurrency(originalCurrency);
              setBudgetLimit(originalBudgetLimit);
            }}
          >
            Discard
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={!isDirty || profileStore.updateState.isLoading}
          >
            {profileStore.updateState.isLoading ? "Saving..." : "Save preferences"}
          </Button>
        </div>
      </form>
    </div>
  );
});
