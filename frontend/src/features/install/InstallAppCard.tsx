import { observer } from "mobx-react-lite";
import { Download, Share } from "lucide-react";

import { Button } from "@/shared/components/Button/Button";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { useStores } from "@/stores/StoreContext";
import { useTranslation, Trans } from "react-i18next";

/**
 * The way to install the app, kept in the profile for whoever dismissed the hint on the
 * dashboard (BRD — F9.8.3). Shown only where installing is possible and not yet done.
 */
export const InstallAppCard = observer(function InstallAppCard() {
  const { installStore } = useStores();
  const { t } = useTranslation("profile");
  const iosSteps = installStore.isIosSafari && !installStore.installed;
  if (!installStore.offersInstall && !iosSteps) return null;

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("install.title")}</CardHeader>
      <CardBody className="flex flex-col gap-3">
        <p className="m-0 text-md leading-relaxed text-muted-foreground">{t("install.body")}</p>
        {installStore.offersInstall ? (
          <Button
            variant="secondary"
            className="min-h-11 w-full md:min-h-0 md:w-auto md:self-start"
            onClick={() => void installStore.install()}
          >
            <Download size={16} aria-hidden="true" />
            {t("install.button")}
          </Button>
        ) : (
          <p className="m-0 text-md text-foreground">
            <Trans
              t={t}
              i18nKey="install.ios"
              components={{
                icon: (
                  <Share
                    size={14}
                    aria-label={t("install.share")}
                    className="inline align-text-bottom"
                  />
                ),
                b: <strong />,
              }}
            />
          </p>
        )}
      </CardBody>
    </Card>
  );
});
