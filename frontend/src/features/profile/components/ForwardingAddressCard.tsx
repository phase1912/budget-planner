import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Check, Copy, RefreshCw } from "lucide-react";

import { Button } from "@/shared/components/Button/Button";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";

/**
 * The user's receipt forwarding address (BRD F11 — F11.2): copy it, or replace it when
 * spam starts reaching it. Replacing is confirmed first, because the old address stops
 * accepting mail the moment it happens.
 */
export const ForwardingAddressCard = observer(function ForwardingAddressCard() {
  const { authStore, profileStore } = useStores();
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
      <CardHeader>Receipts by email</CardHeader>
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="forwarding-address" className="font-semibold text-lg text-foreground">
            Your forwarding address
          </label>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">
            Forward a shop&apos;s e-receipt here from{" "}
            {authStore.user?.email ?? "your account email"}. It is read like a photo and appears on
            Receipts marked as from email. Mail from any other address is ignored.
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
            {copied ? "Copied" : "Copy address"}
          </Button>
        </div>
        {confirming ? (
          <div
            role="alertdialog"
            aria-label="Replace forwarding address"
            className="flex flex-col gap-3 rounded-control border border-border p-3 md:flex-row md:items-center md:justify-between"
          >
            <p className="m-0 text-md text-foreground">
              The current address stops working at once. Replace it?
            </p>
            <div className="flex flex-col gap-2 md:flex-row">
              <Button
                type="button"
                variant="ghost"
                className="min-h-11 w-full md:min-h-0 md:w-auto"
                onClick={() => {
                  setConfirming(false);
                }}
              >
                Keep it
              </Button>
              <Button
                type="button"
                variant="danger"
                className="min-h-11 w-full md:min-h-0 md:w-auto"
                disabled={regenerating}
                onClick={() => void regenerate()}
              >
                {regenerating ? "Replacing…" : "Replace address"}
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
            Get a new address
          </Button>
        )}
      </CardBody>
    </Card>
  );
});
