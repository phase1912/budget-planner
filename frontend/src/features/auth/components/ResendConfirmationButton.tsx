import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/** How long the button waits after sending, so a second press is not a second letter at once. */
const WAIT_SECONDS = 60;

/**
 * Sends the confirmation link again (F17.8.2); full width on a phone. After a letter goes
 * it counts down a minute, so the press visibly did something (F24.3).
 */
export const ResendConfirmationButton = observer(function ResendConfirmationButton() {
  const { accountStore } = useStores();
  const { t } = useTranslation("auth");
  const [now, setNow] = useState(Date.now());
  const sending = accountStore.state.isLoading;
  const resentAt = accountStore.resentAt;
  const left =
    resentAt === null ? 0 : Math.max(0, WAIT_SECONDS - Math.floor((now - resentAt) / 1000));

  useEffect(() => {
    if (resentAt === null) return;
    const tick = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => {
      window.clearInterval(tick);
    };
  }, [resentAt]);

  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      className="min-h-11 w-full md:min-h-0 md:w-auto md:flex-shrink-0"
      disabled={sending || left > 0}
      onClick={() => {
        setNow(Date.now());
        void accountStore.resendConfirmation();
      }}
    >
      {sending
        ? t("banner.sending")
        : left > 0
          ? t("banner.resendIn", { seconds: left })
          : t("banner.resend")}
    </Button>
  );
});
