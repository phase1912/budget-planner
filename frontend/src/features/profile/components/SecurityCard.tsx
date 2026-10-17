import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { Button, Input, Modal, ModalBody, Note, Pill } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Two-factor sign-in (F18.6.1): any account may turn it on, an admin must before the
 * admin pages open. Setting up and turning off happen in dialogs, outside any form.
 */
export const SecurityCard = observer(function SecurityCard() {
  const { twoFactorStore, authStore } = useStores();
  const { t } = useTranslation("profile");
  const [turningOff, setTurningOff] = useState(false);
  const { enabled, setup, recoveryCodes } = twoFactorStore;
  const mustForAdmin = authStore.user?.is_admin === true && !enabled;
  const { hash } = useLocation();
  const card = useRef<HTMLLIElement>(null);

  // The admin pages send an admin here to set it up (F18.6.1).
  useEffect(() => {
    if (hash === "#security") card.current?.scrollIntoView({ block: "start" });
  }, [hash]);

  return (
    <li ref={card} id="security" className="flex scroll-mt-4 flex-col gap-2.5 px-4 py-3">
      <div className="flex min-h-11 items-center gap-3">
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-chip bg-tone-primary-bg text-primary"
        >
          <ShieldCheck size={18} />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="flex flex-wrap items-center gap-2 text-lg font-bold">
            {t("security.label")}
            <Pill tone={enabled ? "success" : "default"} size="sm">
              {enabled ? t("security.on") : t("security.off")}
            </Pill>
          </span>
          <span className="text-sm text-muted-foreground">{t("security.hint")}</span>
        </span>
      </div>
      {enabled ? (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="w-full md:w-auto md:self-end"
          onClick={() => {
            twoFactorStore.close();
            setTurningOff(true);
          }}
        >
          {t("security.turnOff")}
        </Button>
      ) : (
        <Button
          type="button"
          size="sm"
          className="w-full md:w-auto md:self-end"
          disabled={twoFactorStore.state.isLoading}
          onClick={() => {
            void twoFactorStore.begin();
          }}
        >
          {t("security.turnOn")}
        </Button>
      )}
      {mustForAdmin && <Note tone="warning">{t("security.adminNeedsIt")}</Note>}
      {!setup && !turningOff && twoFactorStore.state.error && (
        <Note tone="error">{twoFactorStore.state.error}</Note>
      )}
      {setup && <SetupDialog />}
      {recoveryCodes && <RecoveryCodesDialog codes={recoveryCodes} />}
      {turningOff && (
        <TurnOffDialog
          onClose={() => {
            setTurningOff(false);
            twoFactorStore.close();
          }}
        />
      )}
    </li>
  );
});

const SetupDialog = observer(function SetupDialog() {
  const { twoFactorStore } = useStores();
  const { t } = useTranslation("profile");
  const [code, setCode] = useState("");
  const { setup, state } = twoFactorStore;
  if (!setup) return null;

  return (
    <Modal
      isOpen
      onClose={() => {
        twoFactorStore.close();
      }}
      className="w-full md:max-w-[460px]"
      aria-labelledby="two-factor-setup"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void twoFactorStore.confirm(code);
          }}
        >
          <h2 id="two-factor-setup" className="m-0 text-lg font-bold">
            {t("security.setupTitle")}
          </h2>
          <ol className="m-0 flex flex-col gap-1 pl-5 text-md leading-relaxed text-muted-foreground">
            <li>{t("security.step1")}</li>
            <li>{t("security.step2")}</li>
            <li>{t("security.step3")}</li>
          </ol>
          {/* A white tile in either theme: authenticator apps read dark on light. */}
          <img
            src={`data:image/svg+xml;utf8,${encodeURIComponent(setup.qr_svg)}`}
            alt={t("security.qrAlt")}
            className="mx-auto aspect-square w-48 max-w-full rounded-chip bg-white p-2"
          />
          <p className="m-0 text-base text-muted-foreground">
            {t("security.manual")}{" "}
            <code className="break-all font-mono text-foreground">{setup.secret}</code>
          </p>
          {state.error && <Note tone="error">{state.error}</Note>}
          <Input
            id="two-factor-code"
            label={t("security.code")}
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(event) => {
              setCode(event.target.value);
            }}
            minLength={6}
            maxLength={6}
            required
          />
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto"
              onClick={() => {
                twoFactorStore.close();
              }}
            >
              {t("security.cancel")}
            </Button>
            <Button
              type="submit"
              className="w-full md:w-auto"
              disabled={state.isLoading || code.trim().length < 6}
            >
              {t("security.confirm")}
            </Button>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});

const RecoveryCodesDialog = observer(function RecoveryCodesDialog({ codes }: { codes: string[] }) {
  const { twoFactorStore } = useStores();
  const { t } = useTranslation("profile");

  return (
    <Modal
      isOpen
      onClose={() => {
        twoFactorStore.close();
      }}
      className="w-full md:max-w-[460px]"
      aria-labelledby="recovery-codes"
    >
      <ModalBody className="flex flex-col gap-4">
        <h2 id="recovery-codes" className="m-0 text-lg font-bold">
          {t("security.codesTitle")}
        </h2>
        <p className="m-0 text-md leading-relaxed text-muted-foreground">
          {t("security.codesBody")}
        </p>
        <ul className="m-0 grid list-none grid-cols-2 gap-2 p-0 font-mono text-md">
          {codes.map((code) => (
            <li key={code} className="rounded-chip bg-muted px-3 py-2 text-center">
              {code}
            </li>
          ))}
        </ul>
        <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
          <Button
            type="button"
            variant="secondary"
            className="w-full md:w-auto"
            onClick={() => {
              void navigator.clipboard.writeText(codes.join("\n"));
            }}
          >
            {t("security.copy")}
          </Button>
          <Button
            type="button"
            className="w-full md:w-auto"
            onClick={() => {
              twoFactorStore.close();
            }}
          >
            {t("security.saved")}
          </Button>
        </div>
      </ModalBody>
    </Modal>
  );
});

const TurnOffDialog = observer(function TurnOffDialog({ onClose }: { onClose: () => void }) {
  const { twoFactorStore } = useStores();
  const { t } = useTranslation("profile");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const { state } = twoFactorStore;

  return (
    <Modal
      isOpen
      onClose={onClose}
      className="w-full md:max-w-[460px]"
      aria-labelledby="two-factor-off"
    >
      <ModalBody>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void twoFactorStore.disable(password, code).then((done) => {
              if (done) onClose();
            });
          }}
        >
          <h2 id="two-factor-off" className="m-0 text-lg font-bold">
            {t("security.offTitle")}
          </h2>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">
            {t("security.offBody")}
          </p>
          {state.error && <Note tone="error">{state.error}</Note>}
          <Input
            id="two-factor-password"
            type="password"
            autoComplete="current-password"
            label={t("security.password")}
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
            required
          />
          <Input
            id="two-factor-off-code"
            label={t("security.codeOrRecovery")}
            autoComplete="one-time-code"
            value={code}
            onChange={(event) => {
              setCode(event.target.value);
            }}
            minLength={6}
            maxLength={16}
            required
          />
          <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto"
              onClick={onClose}
            >
              {t("security.cancel")}
            </Button>
            <Button
              type="submit"
              variant="danger"
              className="w-full md:w-auto"
              disabled={state.isLoading || !password || code.trim().length < 6}
            >
              {t("security.turnOff")}
            </Button>
          </div>
        </form>
      </ModalBody>
    </Modal>
  );
});
