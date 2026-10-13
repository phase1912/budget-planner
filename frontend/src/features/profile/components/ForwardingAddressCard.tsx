import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Check, Copy, RefreshCw } from "lucide-react";

import { Button } from "@/shared/components/Button/Button";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";
import { useTranslation } from "react-i18next";

/**
 * The user's receipt forwarding address (BRD F11 — F11.2): copy it, or replace it when
 * spam starts reaching it. Replacing is confirmed first, because the old address stops
 * accepting mail the moment it happens.
 */
export const ForwardingAddressCard = observer(function ForwardingAddressCard() {
  const { authStore, profileStore } = useStores();
  const { t } = useTranslation("profile");
  const [copied, setCopied] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const address = authStore.user?.forwarding_address ?? "";
  const regenerating = profileStore.regenerateState.isLoading;

  const copy = async () => {
    await navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };

  const regenerate = async () => {
    if (await profileStore.regenerateForwardingAddress()) setConfirming(false);
  };

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("forwarding.title")}</CardHeader>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="forwarding-address" className="font-semibold text-lg text-foreground">
            {t("forwarding.label")}
          </label>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">
            {t("forwarding.hint", {
              email: authStore.user?.email ?? t("forwarding.yourEmail"),
            })}
          </p>
        </div>
        <div className="flex flex-col gap-2 md:flex-row md:items-center">
          <output
            id="forwarding-address"
            className="min-h-11 min-w-0 flex-1 break-all rounded-control border border-border bg-muted px-3 py-2.5 font-mono text-md text-foreground md:min-h-0"
          >
            {address}
          </output>
          <Button
            type="button"
            variant="secondary"
            className="min-h-11 w-full md:min-h-0 md:w-auto"
            onClick={() => void copy()}
          >
            {copied ? (
              <Check size={16} aria-hidden="true" />
            ) : (
              <Copy size={16} aria-hidden="true" />
            )}
            {copied ? t("forwarding.copied") : t("forwarding.copy")}
          </Button>
        </div>
        {confirming ? (
          <div
            role="alertdialog"
            aria-label={t("forwarding.replaceLabel")}
            className="flex flex-col gap-3 rounded-control border border-border p-3 md:flex-row md:items-center md:justify-between"
          >
            <p className="m-0 text-md text-foreground">{t("forwarding.replaceQuestion")}</p>
            <div className="flex flex-col gap-2 md:flex-row">
              <Button
                type="button"
                variant="ghost"
                className="min-h-11 w-full md:min-h-0 md:w-auto"
                onClick={() => {
                  setConfirming(false);
                }}
              >
                {t("forwarding.keep")}
              </Button>
              <Button
                type="button"
                variant="danger"
                className="min-h-11 w-full md:min-h-0 md:w-auto"
                disabled={regenerating}
                onClick={() => void regenerate()}
              >
                {regenerating ? t("forwarding.replacing") : t("forwarding.replace")}
              </Button>
            </div>
          </div>
        ) : (
          <Button
            type="button"
            variant="ghost"
            className="min-h-11 w-full md:min-h-0 md:w-auto md:self-start"
            onClick={() => {
              setConfirming(true);
            }}
          >
            <RefreshCw size={16} aria-hidden="true" />
            {t("forwarding.new")}
          </Button>
        )}
      </CardBody>
    </Card>
  );
});
