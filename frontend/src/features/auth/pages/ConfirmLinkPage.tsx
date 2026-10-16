import { useEffect, useRef } from "react";
import { observer } from "mobx-react-lite";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { LoadingState, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { AuthCard } from "../components/AuthCard";

/**
 * Where a confirmation link from a letter lands (F17.8.2-3): `address` confirms the
 * account's address, `change` switches the account to a new one. Works signed in or
 * out, as the letter may be opened on another device.
 */
export const ConfirmLinkPage = observer(function ConfirmLinkPage({
  kind,
}: {
  kind: "address" | "change";
}) {
  const { accountStore, authStore } = useStores();
  const { t } = useTranslation("auth");
  const [params] = useSearchParams();
  const token = params.get("token");
  const followed = useRef(false);
  const { state } = accountStore;

  useEffect(() => {
    // Followed once: a change link is spent by its first use.
    if (!token || followed.current) return;
    followed.current = true;
    accountStore.reset();
    void (kind === "address"
      ? accountStore.confirmEmail(token)
      : accountStore.confirmEmailChange(token));
  }, [accountStore, kind, token]);

  const onward = authStore.isAuthenticated ? (
    <Link to="/" className="text-center text-base text-primary hover:underline">
      {t("confirm.open")}
    </Link>
  ) : (
    <Link to="/login" className="text-center text-base text-primary hover:underline">
      {t("confirm.signIn")}
    </Link>
  );

  return (
    <AuthCard title={t("confirm.title")}>
      {!token ? (
        <Note tone="warning">{t("confirm.noLink")}</Note>
      ) : state.status === "success" ? (
        <Note tone="success">
          {kind === "address"
            ? t("confirm.done")
            : t("confirm.changed", { email: accountStore.confirmedEmail ?? "" })}
        </Note>
      ) : state.status === "error" ? (
        <Note tone="error">{state.error}</Note>
      ) : (
        <LoadingState title={t("confirm.checking")} />
      )}
      {onward}
    </AuthCard>
  );
});
