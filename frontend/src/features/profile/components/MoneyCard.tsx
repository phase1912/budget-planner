import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Select } from "@/shared/components";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { CurrencySelect } from "@/shared/components/CurrencySelect/CurrencySelect";
import { useStores } from "@/stores/StoreContext";

const DAYS = Array.from({ length: 30 }, (_, i) => i + 1);

/**
 * Money settings (F1.4, F23.10): the currency every figure is in, the monthly budget, the
 * income that usually comes in and the day it comes. Saved together with its own button;
 * the currency is locked by the server once receipts exist.
 */
export const MoneyCard = observer(function MoneyCard() {
  const { authStore, profileStore } = useStores();
  const { t } = useTranslation("profile");
  const user = authStore.user;
  const saved = {
    currency: user?.currency ?? "PLN",
    budget: user?.budget_limit?.toString() ?? "",
    income: user?.usual_income?.toString() ?? "",
    payday: user?.payday ? String(user.payday) : "",
  };
  const [form, setForm] = useState(saved);
  const key = JSON.stringify(saved);
  useEffect(() => {
    setForm(JSON.parse(key) as typeof saved);
  }, [key]);
  const dirty = JSON.stringify(form) !== key;
  const set = (field: keyof typeof form) => (value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
  };
  const amount = (text: string) => (text.trim() === "" ? null : text.trim().replace(",", "."));

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("money.title")}</CardHeader>
      <CardBody>
        <form
          className="flex flex-col gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            void profileStore.updateProfile({
              currency: form.currency,
              budget_limit: amount(form.budget),
              usual_income: amount(form.income),
              payday: form.payday ? Number(form.payday) : null,
            });
          }}
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="currency" className="text-base font-medium text-muted-foreground">
                {t("money.currency")}
              </label>
              <CurrencySelect
                id="currency"
                value={form.currency}
                onChange={(e) => {
                  set("currency")(e.target.value);
                }}
              />
            </div>
            <Input
              id="budget-limit"
              label={t("money.limit")}
              inputMode="decimal"
              value={form.budget}
              placeholder={t("money.none")}
              onChange={(e) => {
                set("budget")(e.target.value);
              }}
            />
            <Input
              id="usual-income"
              label={t("money.income")}
              inputMode="decimal"
              value={form.income}
              placeholder={t("money.none")}
              onChange={(e) => {
                set("income")(e.target.value);
              }}
            />
            <Select
              id="payday"
              label={t("money.payday")}
              value={form.payday}
              onChange={(e) => {
                set("payday")(e.target.value);
              }}
            >
              <option value="">{t("money.noPayday")}</option>
              {DAYS.map((day) => (
                <option key={day} value={day}>
                  {day}
                </option>
              ))}
              <option value="31">{t("money.lastDay")}</option>
            </Select>
          </div>
          <p className="m-0 text-md text-muted-foreground">{t("money.hint")}</p>
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <Button
              type="button"
              variant="ghost"
              disabled={!dirty}
              onClick={() => {
                setForm(saved);
              }}
            >
              {t("discard")}
            </Button>
            <Button type="submit" disabled={!dirty || profileStore.updateState.isLoading}>
              {profileStore.updateState.isLoading ? t("saving") : t("save")}
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  );
});
