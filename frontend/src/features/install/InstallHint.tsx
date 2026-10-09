import { observer } from "mobx-react-lite";
import { Download, Share, X } from "lucide-react";

import { Button, IconButton, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Offer to put the app on the home screen (BRD — F9.8.3). On Android Chrome it opens the
 * browser's own install dialog; on iPhone Safari, which has none, it says where the step
 * is. Dismissible, and gone for good once the app runs installed.
 */
export const InstallHint = observer(function InstallHint() {
  const { installStore } = useStores();
  if (installStore.dismissed) return null;
  if (!installStore.offersInstall && !installStore.showsIosHint) return null;

  return (
    <Note tone="info">
      <div className="flex items-start gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <p className="m-0 font-semibold">Put Budget Agent on your home screen</p>
          {installStore.offersInstall ? (
            <>
              <p className="m-0">It opens full screen like an app, straight to your receipts.</p>
              <Button
                variant="secondary"
                size="sm"
                className="min-h-11 w-full md:min-h-0 md:w-auto md:self-start"
                onClick={() => void installStore.install()}
              >
                <Download size={15} aria-hidden="true" />
                Install app
              </Button>
            </>
          ) : (
            <p className="m-0">
              Tap <Share size={14} aria-label="Share" className="inline align-text-bottom" /> Share
              in Safari, then <strong>Add to Home Screen</strong>. It then opens full screen like an
              app.
            </p>
          )}
        </div>
        <IconButton
          aria-label="Dismiss the install hint"
          className="shrink-0"
          onClick={() => {
            installStore.dismiss();
          }}
        >
          <X size={16} aria-hidden="true" />
        </IconButton>
      </div>
    </Note>
  );
});
