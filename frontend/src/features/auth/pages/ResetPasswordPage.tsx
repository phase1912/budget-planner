import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button, Input, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { AuthCard } from "../components/AuthCard";
import { PasswordChecklist } from "../components/PasswordChecklist";
import { passwordIsValid } from "../passwordRules";

/** Setting a new password from the link in a reset letter; every session ends (F17.8.3). */
export const ResetPasswordPage = observer(function ResetPasswordPage() {
  const { accountStore } = useStores();
  const { t } = useTranslation("auth");
  const [params] = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const { state } = accountStore;

  useEffect(() => {
    accountStore.reset();
  }, [accountStore]);

  const body = !token ? (
    <>
      <Note tone="warning">{t("reset.noLink")}</Note>
      <Link to="/forgot-password" className="text-center text-base text-primary hover:underline">
        {t("reset.again")}
      </Link>
    </>
  ) : state.status === "success" ? (
    <>
      <Note tone="success">{t("reset.done")}</Note>
      <Link to="/login" className="text-center text-base text-primary hover:underline">
        {t("reset.signIn")}
      </Link>
    </>
  ) : (
    <form
      className="flex flex-col gap-5"
      onSubmit={(event) => {
        event.preventDefault();
        void accountStore.resetPassword(token, password);
      }}
    >
      {state.error && (
        <Note tone="error">
          {state.error}{" "}
          <Link to="/forgot-password" className="text-primary hover:underline">
            {t("reset.again")}
          </Link>
        </Note>
      )}
      <Input
        id="password"
        type="password"
        autoComplete="new-password"
        label={t("fields.password")}
        value={password}
        onChange={(event) => {
          setPassword(event.target.value);
        }}
        required
      />
      <Input
        id="confirm-password"
        type="password"
        autoComplete="new-password"
        label={t("fields.confirmPassword")}
        value={confirm}
        onChange={(event) => {
          setConfirm(event.target.value);
        }}
        required
      />
      <PasswordChecklist password={password} confirm={confirm} />
      <Button
        type="submit"
        size="lg"
        disabled={state.isLoading || !passwordIsValid(password) || password !== confirm}
      >
        {state.isLoading ? t("reset.submitting") : t("reset.submit")}
      </Button>
    </form>
  );

  return (
    <AuthCard title={t("reset.title")} subtitle={token ? t("reset.subtitle") : undefined}>
      {body}
    </AuthCard>
  );
});
