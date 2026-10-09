import { observer } from "mobx-react-lite";
import { Download, Share } from "lucide-react";

import { Button } from "@/shared/components/Button/Button";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";

/**
 * The way to install the app, kept in the profile for whoever dismissed the hint on the
 * dashboard (BRD — F9.8.3). Shown only where installing is possible and not yet done.
 */
export const InstallAppCard = observer(function InstallAppCard() {
  const { installStore } = useStores();
  const iosSteps = installStore.isIosSafari && !installStore.installed;
  if (!installStore.offersInstall && !iosSteps) return null;

  return (
    <Card variant="surface" flush>
      <CardHeader>App</CardHeader>
      <CardBody className="flex flex-col gap-3">
        <p className="m-0 text-md leading-relaxed text-muted-foreground">
          Budget Agent installs on this device and opens full screen, like any other app. No app
          store needed, and it always runs the latest version.
        </p>
        {installStore.offersInstall ? (
          <Button
            variant="secondary"
            className="min-h-11 w-full md:min-h-0 md:w-auto md:self-start"
            onClick={() => void installStore.install()}
          >
            <Download size={16} aria-hidden="true" />
            Install app
          </Button>
        ) : (
          <p className="m-0 text-md text-foreground">
            In Safari, tap{" "}
            <Share size={14} aria-label="Share" className="inline align-text-bottom" /> Share, then{" "}
            <strong>Add to Home Screen</strong>.
          </p>
        )}
      </CardBody>
    </Card>
  );
});
