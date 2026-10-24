import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Note } from "@/shared/components";
import { Download, FileText, Trash2 } from "lucide-react";
import { SettingsRow } from "./SettingsRows";
import { useStores } from "@/stores/StoreContext";

/**
 * The user's rights over their data (F17.9.1-2, GDPR art. 15, 17, 20), as Settings rows:
 * everything held about them in one archive, and the account deleted with all of it.
 */
export const DataCard = observer(function DataCard() {
  const { exportStore, accountStore } = useStores();
  const { t } = useTranslation("profile");
  const [deleting, setDeleting] = useState(false);
  const exporting = Boolean(exportStore.busy.account);

  return (
    <>
      <SettingsRow
        icon={Download}
        color="var(--cat-dining)"
        label={t("data.export")}
        hint={t("data.exportHint")}
        value={exporting ? t("data.exporting") : "ZIP"}
        onClick={() => {
          if (!exporting)
            void exportStore.start({ kind: "account", format: "zip", compare: false });
        }}
      />
      <SettingsRow
        icon={Trash2}
        danger
        label={t("data.delete")}
        hint={t("data.deleteHint")}
        onClick={() => {
          accountStore.reset();
          setDeleting(true);
        }}
      />
      <SettingsRow
        icon={FileText}
        color="var(--cat-other)"
        label={t("data.privacy")}
        to="/privacy"
      />
      <SettingsRow icon={FileText} color="var(--cat-other)" label={t("data.terms")} to="/terms" />
      {deleting && (
        <DeleteAccountDialog
          onClose={() => {
            setDeleting(false);
          }}
        />
      )}
    </>
  );
});

const DeleteAccountDialog = observer(function DeleteAccountDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const { accountStore, authStore } = useStores();
  const { t } = useTranslation("profile");
  const [password, setPassword] = useState("");
  // An account opened with Google or Apple has no password: its address confirms (F1.6).
  const byEmail = authStore.user?.has_password === false;
  const { state } = accountStore;

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[460px]"
      aria-labelledby="delete-account"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void accountStore.deleteAccount(password);
          }}
        >
          <h2 id="delete-account" className="m-0 text-lg font-bold">
            {t("data.dialogTitle")}
          </h2>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">
            {t("data.dialogBody")}
          </p>
          {state.error && <Note tone="error">{state.error}</Note>}
          <Input
            id="delete-password"
            type={byEmail ? "email" : "password"}
            autoComplete={byEmail ? "off" : "current-password"}
            label={byEmail ? t("signInMethods.deleteWithEmail") : t("data.password")}
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
            required
          />
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto"
              onClick={onClose}
            >
              {t("data.cancel")}
            </Button>
            <Button
              type="submit"
              variant="danger"
              className="w-full md:w-auto"
              disabled={state.isLoading || !password}
            >
              {state.isLoading ? t("data.deleting") : t("data.confirm")}
            </Button>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
