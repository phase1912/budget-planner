import { useEffect } from "react";
import { X } from "lucide-react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";

import { IconButton, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { numberFormat, dateFormat } from "@/i18n/format";
import { useTranslation, Trans } from "react-i18next";

const MONTH = dateFormat({ month: "long" });
const MONEY = numberFormat({
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Goals heading over their cap this month, waiting for the user without their asking
 * (BRD F7 — F8.8). Each says how far over the month is heading and where the advice
 * to correct course is: the background pass has already prepared it. Set aside, a
 * warning stays away until next month. Shown on the dashboard and on Goals.
 */
export const AtRiskWarnings = observer(function AtRiskWarnings({
  linkToGoals = false,
}: {
  /** Point to the Goals screen for the advice; off when already on it. */
  linkToGoals?: boolean;
}) {
  const { adviceStore, authStore } = useStores();
  const { t } = useTranslation("goals");
  const currency = authStore.user?.currency ?? "PLN";
  const money = (amount: string | number) => `${MONEY.format(Number(amount))} ${currency}`;
  const month = MONTH.format(new Date());

  useEffect(() => {
    void adviceStore.loadProgress();
  }, [adviceStore]);

  if (adviceStore.warnings.length === 0) return null;

  return (
    <ul aria-label={t("risk.list")} className="m-0 flex list-none flex-col gap-3 p-0">
      {adviceStore.warnings.map((pace) => (
        <li key={pace.goal_id}>
          <Note tone="warning">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 flex-col gap-1">
                <span className="font-semibold">{t("risk.heading", { name: pace.goal_name })}</span>
                <span>
                  <Trans
                    t={t}
                    i18nKey="risk.body"
                    values={{
                      spent: money(pace.spent),
                      target: money(pace.target),
                      month,
                      projected: money(pace.projected),
                      over: money(-Number(pace.margin)),
                    }}
                    components={{ b: <strong /> }}
                  />
                </span>
                {linkToGoals ? (
                  <Link to="/goals" className="font-semibold text-inherit underline">
                    {t("risk.seeHow")}
                  </Link>
                ) : (
                  <span>{t("risk.below")}</span>
                )}
              </div>
              <IconButton
                aria-label={t("risk.dismiss", { name: pace.goal_name })}
                className="h-11 w-11 shrink-0 md:h-auto md:w-auto"
                onClick={() => void adviceStore.dismissWarning(pace.goal_id)}
              >
                <X size={16} aria-hidden="true" />
              </IconButton>
            </div>
          </Note>
        </li>
      ))}
    </ul>
  );
});
