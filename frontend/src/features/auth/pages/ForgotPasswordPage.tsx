import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button, Input, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { AuthCard } from "../components/AuthCard";

/**
 * Asking for a password reset link (F17.8.3). The answer reads the same whether the
 * address has an account or not, so the form cannot be used to find accounts.
 */
export const ForgotPasswordPage = observer(function ForgotPasswordPage() {
  const { accountStore } = useStores();
  const { t } = useTranslation("auth");
  const [email, setEmail] = useState("");
  const { state } = accountStore;

  useEffect(() => {
    accountStore.reset();
  }, [accountStore]);

  return (
    <AuthCard title={t("forgot.title")} subtitle={t("forgot.subtitle")}>
      {state.status === "success" ? (
        <Note tone="success">{t("forgot.sent", { email })}</Note>
      ) : (
        <form
          className="flex flex-col gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            void accountStore.forgotPassword(email);
          }}
        >
          {state.error && <Note tone="error">{state.error}</Note>}
          <Input
            id="email"
            type="email"
            label={t("fields.email")}
            placeholder={t("fields.emailPlaceholder")}
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
            required
          />
          <Button type="submit" size="lg" disabled={state.isLoading}>
            {state.isLoading ? t("forgot.submitting") : t("forgot.submit")}
          </Button>
        </form>
      )}
      <Link to="/login" className="text-center text-base text-primary hover:underline">
        {t("forgot.back")}
      </Link>
    </AuthCard>
  );
});
