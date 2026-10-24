import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Note } from "@/shared/components";
import { ResendConfirmationButton } from "@/features/auth/components/ResendConfirmationButton";
import { useStores } from "@/stores/StoreContext";

/**
 * Tells a user who has not confirmed their address what waits on it, with the link
 * sent again on request (F17.8.2). The upload screen says it in its own place instead.
 */
export const ConfirmEmailBanner = observer(function ConfirmEmailBanner() {
  const { accountStore, authStore } = useStores();
  const { pathname } = useLocation();
  const { t } = useTranslation("auth");
  const waiting = accountStore.mustConfirm;
  // Confirmed in another tab or the mail app: gone as soon as this tab is looked at again.
  useEffect(() => {
    if (!waiting) return;
    const look = () => {
      if (document.visibilityState === "visible") void accountStore.checkConfirmed();
    };
    window.addEventListener("focus", look);
    document.addEventListener("visibilitychange", look);
    return () => {
      window.removeEventListener("focus", look);
      document.removeEventListener("visibilitychange", look);
    };
  }, [waiting, accountStore]);
  if (!accountStore.mustConfirm || pathname.startsWith("/upload")) return null;
  const email = authStore.user?.email ?? "";
  return (
    <Note tone="warning" className="mt-3 mb-1 md:mt-0 md:mb-6">
      <span className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <span>
          <span className="md:hidden">{t("banner.short", { email })}</span>
          <span className="hidden md:inline">{t("banner.text", { email })}</span>
        </span>
        <ResendConfirmationButton />
      </span>
    </Note>
  );
});
