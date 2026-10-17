import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { Switch } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Business trips — per diem and the settlement for an employer — are for people who
 * travel for work (F23.12); everyone else never sees them. Holidays are in Plan either way.
 */
export const WorkTripsCard = observer(function WorkTripsCard() {
  const { authStore, profileStore } = useStores();
  const { t } = useTranslation("profile");
  const on = authStore.user?.travels_for_work === true;

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("work.title")}</CardHeader>
      <CardBody className="flex flex-col gap-3">
        <Switch
          checked={on}
          onChange={(value) => {
            void profileStore.saveQuietly({ travels_for_work: value });
          }}
          label={t("work.label")}
          hint={t("work.hint")}
        />
        {on && (
          <Link to="/trips?kind=business" className="text-lg font-semibold text-primary">
            {t("work.open")}
          </Link>
        )}
      </CardBody>
    </Card>
  );
});
