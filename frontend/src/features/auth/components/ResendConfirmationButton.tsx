import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/** Sends the confirmation link again (F17.8.2); full width on a phone. */
export const ResendConfirmationButton = observer(function ResendConfirmationButton() {
  const { accountStore } = useStores();
  const { t } = useTranslation("auth");
  const sending = accountStore.state.isLoading;
  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      className="min-h-11 w-full md:min-h-0 md:w-auto md:flex-shrink-0"
      disabled={sending}
      onClick={() => {
        void accountStore.resendConfirmation();
      }}
    >
      {sending ? t("banner.sending") : t("banner.resend")}
    </Button>
  );
});
