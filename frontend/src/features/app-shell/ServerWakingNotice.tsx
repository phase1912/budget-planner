import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { useStores } from "@/stores/StoreContext";

/**
 * Says the server is starting while reads wait on a cold start (F0.9), so a 20-second
 * load reads as expected rather than as a hung app. Sits above the phone's bottom bar.
 */
export const ServerWakingNotice = observer(function ServerWakingNotice() {
  const { serverStore } = useStores();
  const { t } = useTranslation();
  if (!serverStore.isWaking) return null;
  return (
    <div className="fixed inset-x-4 bottom-24 z-60 flex justify-center md:bottom-6">
      <p
        role="status"
        className="m-0 max-w-md rounded-control border border-tone-info-border bg-background px-4 py-3 text-base font-medium text-tone-info-text shadow-lg"
      >
        {t("serverWaking")}
      </p>
    </div>
  );
});
