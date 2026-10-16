import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Moving the account to another address (F17.8.3): a link goes to the new one, and the
 * account switches only once it is followed. The password is asked again, so a screen
 * left signed in cannot give the account away.
 */
export const ChangeEmailDialog = observer(function ChangeEmailDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const { accountStore } = useStores();
  const { t } = useTranslation("profile");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { state } = accountStore;
  const sent = state.status === "success";

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[460px]"
      aria-labelledby="change-email"
    >
      <ModalBody className="flex flex-col gap-4">
        <h2 id="change-email" className="m-0 text-lg font-bold">
          {t("account.changeTitle")}
        </h2>
        {sent ? (
          <>
            <Note tone="success">{t("account.sent", { email })}</Note>
            <Button type="button" className="w-full md:w-auto md:self-end" onClick={onClose}>
              {t("account.close")}
            </Button>
          </>
        ) : (
          <form
            className="flex flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              void accountStore.changeEmail(email, password);
            }}
          >
            <p className="m-0 text-md leading-relaxed text-muted-foreground">
              {t("account.changeHint")}
            </p>
            {state.error && <Note tone="error">{state.error}</Note>}
            <Input
              id="new-email"
              type="email"
              autoComplete="email"
              label={t("account.newEmail")}
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
              }}
              required
            />
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              label={t("account.password")}
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
                {t("account.cancel")}
              </Button>
              <Button type="submit" className="w-full md:w-auto" disabled={state.isLoading}>
                {state.isLoading ? t("account.sending") : t("account.send")}
              </Button>
            </div>
          </form>
        )}
      </ModalBody>
    </Modal>
  );
});
