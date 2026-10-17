import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { PalettePicker, Switch } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * The look of the product (F23.1): six palettes, each previewed in its own colours — a
 * tile carries the palette's attribute, so the tokens inside it are that palette's — and
 * Midnight at night if wanted. A choice paints at once and is kept on the account.
 */
export const AppearanceCard = observer(function AppearanceCard() {
  const { themeStore, profileStore } = useStores();
  const { t } = useTranslation("profile");

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("appearance.title")}</CardHeader>
      <CardBody className="flex flex-col gap-4">
        <PalettePicker
          label={t("appearance.palette")}
          value={themeStore.palette}
          onChange={(palette) => {
            void profileStore.choosePalette(palette);
          }}
        />
        <Switch
          checked={themeStore.darkAtNight}
          onChange={(on) => {
            void profileStore.chooseDarkAtNight(on);
          }}
          label={t("appearance.darkAtNight")}
          hint={t("appearance.darkAtNightHint")}
        />
      </CardBody>
    </Card>
  );
});
