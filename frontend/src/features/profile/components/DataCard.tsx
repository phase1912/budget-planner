import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Note } from "@/shared/components";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";

/**
 * The user's rights over their data (F17.9.1-2, GDPR art. 15, 17, 20): everything held
 * about them in one archive, and the account deleted with all of it.
 */
export const DataCard = observer(function DataCard() {
  const { exportStore, accountStore } = useStores();
  const { t } = useTranslation("profile");
  const [deleting, setDeleting] = useState(false);
  const exporting = Boolean(exportStore.busy.account);

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("data.title")}</CardHeader>
      <CardBody className="flex flex-col gap-5.5">
        <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center md:gap-8">
          <div className="flex w-full max-w-md flex-col gap-1">
            <span className="text-lg font-semibold text-foreground">{t("data.exportLabel")}</span>
            <span className="text-md leading-relaxed text-muted-foreground">
              {t("data.exportHint")}
            </span>
          </div>
          <Button
            type="button"
            variant="secondary"
            className="w-full md:w-auto"
            disabled={exporting}
            onClick={() => {
              void exportStore.start({ kind: "account", format: "zip", compare: false });
            }}
          >
            {exporting ? t("data.exporting") : t("data.export")}
          </Button>
        </div>

        <div className="h-px bg-border" />

        <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center md:gap-8">
          <div className="flex w-full max-w-md flex-col gap-1">
            <span className="text-lg font-semibold text-foreground">{t("data.deleteLabel")}</span>
            <span className="text-md leading-relaxed text-muted-foreground">
              {t("data.deleteHint")}
            </span>
          </div>
          <Button
            type="button"
            variant="danger"
            className="w-full md:w-auto"
            onClick={() => {
              accountStore.reset();
              setDeleting(true);
            }}
          >
            {t("data.delete")}
          </Button>
        </div>

        <nav className="flex flex-wrap gap-x-5 gap-y-2 text-base">
          <Link to="/privacy" className="text-primary hover:underline">
            {t("data.privacy")}
          </Link>
          <Link to="/terms" className="text-primary hover:underline">
            {t("data.terms")}
          </Link>
        </nav>
      </CardBody>
      {deleting && (
        <DeleteAccountDialog
          onClose={() => {
            setDeleting(false);
          }}
        />
      )}
    </Card>
  );
});

const DeleteAccountDialog = observer(function DeleteAccountDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const { accountStore } = useStores();
  const { t } = useTranslation("profile");
  const [password, setPassword] = useState("");
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
            type="password"
            autoComplete="current-password"
            label={t("data.password")}
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
