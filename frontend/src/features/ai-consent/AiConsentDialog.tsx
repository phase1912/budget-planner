import { useId, useState } from "react";
import { observer } from "mobx-react-lite";
import { Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button, IconTile, Modal, ModalBody, ModalFooter } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Asks once, before anything of the account goes to the AI provider (F25.3.2, App Review
 * 5.1.2): what is sent, to whom, and why. Allowing turns every AI feature on; "not now"
 * leaves them waiting — typing receipts and expenses by hand still works — and the
 * question comes back on the next visit, or from Settings.
 */
export const AiConsentDialog = observer(function AiConsentDialog() {
  const { authStore, profileStore } = useStores();
  const { t } = useTranslation("profile");
  const titleId = useId();
  const [later, setLater] = useState(false);
  const [saving, setSaving] = useState(false);
  const user = authStore.user;
  if (!user || user.ai_consent_at || later) return null;

  const close = () => {
    setLater(true);
  };
  return (
    <Modal isOpen onClose={close} aria-labelledby={titleId} className="md:w-[520px]">
      <ModalBody className="flex flex-col gap-4">
        <div className="flex items-start gap-3.5">
          <IconTile tone="accent" size="lg">
            <Sparkles size={20} aria-hidden="true" />
          </IconTile>
          <div className="flex min-w-0 flex-col gap-1">
            <h2 id={titleId} className="m-0 text-[17px] font-bold">
              {t("aiConsent.title")}
            </h2>
            <p className="m-0 text-md text-muted-foreground">{t("aiConsent.lead")}</p>
          </div>
        </div>
        <ul className="m-0 flex list-disc flex-col gap-1.5 pl-5 text-md">
          <li>{t("aiConsent.what")}</li>
          <li>{t("aiConsent.who")}</li>
          <li>{t("aiConsent.why")}</li>
          <li>{t("aiConsent.withdraw")}</li>
        </ul>
      </ModalBody>
      <ModalFooter>
        <span className="hidden md:block" />
        <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
          <Button type="button" variant="ghost" onClick={close}>
            {t("aiConsent.later")}
          </Button>
          <Button
            type="button"
            disabled={saving}
            onClick={() => {
              setSaving(true);
              void profileStore.setAiConsent(true).finally(() => {
                setSaving(false);
              });
            }}
          >
            {t("aiConsent.allow")}
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  );
});
