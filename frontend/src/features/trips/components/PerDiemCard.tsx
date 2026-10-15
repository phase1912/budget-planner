import { useState } from "react";
import { Calculator } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { dateFormat, formatAmount, numberFormat } from "@/i18n/format";
import { Button, Card } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { TripDetail } from "@/stores/TripsStore";
import { countryName } from "../tripFormat";
import { PerDiemDialog } from "./PerDiemDialog";

const RATE = numberFormat({ minimumFractionDigits: 4, maximumFractionDigits: 4 });
const RATE_DAY = dateFormat({ day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/**
 * A business trip's per diem under the Polish rules (F20.4, ADR-0018): each 24-hour day,
 * the share of the rate its hours earn and the paragraph that says so, the meals that
 * took their part off, each part's total in its currency, and the whole in złoty at the
 * NBP rate it was put into złoty at. Before the times are given, the way to give them.
 */
export const PerDiemCard = observer(function PerDiemCard({ trip }: { trip: TripDetail }) {
  const { tripsStore } = useStores();
  const { t } = useTranslation("trips");
  const [editing, setEditing] = useState(false);
  const perDiem = trip.per_diem;

  return (
    <Card className="flex flex-col gap-3 p-4 md:p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h2 className="m-0 flex items-center gap-2 text-lg font-bold">
          <Calculator size={18} aria-hidden="true" className="shrink-0" />
          {t("perDiem.title")}
        </h2>
        {perDiem && (
          <div className="flex gap-2 [&>*]:flex-1 md:[&>*]:flex-none">
            <Button
              size="sm"
              variant="secondary"
              className="min-h-11 md:min-h-0"
              onClick={() => {
                setEditing(true);
              }}
            >
              {t("perDiem.edit")}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="min-h-11 md:min-h-0"
              onClick={() => void tripsStore.clearTimes(trip.id)}
            >
              {t("perDiem.remove")}
            </Button>
          </div>
        )}
      </div>

      {!perDiem ? (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="m-0 text-md text-muted-foreground">{t("perDiem.none")}</p>
          <Button
            className="w-full shrink-0 md:w-auto"
            onClick={() => {
              setEditing(true);
            }}
          >
            {t("perDiem.workOut")}
          </Button>
        </div>
      ) : (
        <>
          {perDiem.parts.map((part) => (
            <section key={part.country} className="flex flex-col gap-1.5">
              <h3 className="m-0 text-md font-semibold text-muted-foreground">
                {part.abroad
                  ? t("perDiem.abroad", {
                      country: countryName(part.country),
                      rate: formatAmount(part.rate),
                      currency: part.currency,
                    })
                  : t("perDiem.home", { rate: formatAmount(part.rate), currency: part.currency })}
              </h3>
              <ul className="m-0 flex list-none flex-col p-0">
                {part.days.map((day) => (
                  <li
                    key={day.number}
                    className="flex flex-col gap-0.5 border-b border-border py-2 last:border-b-0"
                  >
                    <span className="flex items-baseline justify-between gap-3 text-md">
                      <span className="font-semibold">
                        {t("perDiem.day", { number: day.number })}
                      </span>
                      <span className="tabular-nums font-semibold">
                        {formatAmount(day.due)} {part.currency}
                      </span>
                    </span>
                    <span className="text-base text-muted-foreground">
                      {t("perDiem.hours", { hours: formatAmount(day.hours) })} ·{" "}
                      {t("perDiem.share", { percent: Math.round(Number(day.share) * 100) })} ·{" "}
                      {day.rule}
                    </span>
                    {day.meals.length > 0 && (
                      <span className="text-base text-muted-foreground">
                        {day.meals.map((meal) => t(`perDiem.meal.${meal}`)).join(", ")} ·{" "}
                        {day.meals_rule} ·{" "}
                        <span className="tabular-nums">
                          −{formatAmount(day.reduction)} {part.currency}
                        </span>
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              <p className="m-0 flex items-baseline justify-between gap-3 text-md font-bold">
                <span>{t("perDiem.partTotal")}</span>
                <span className="tabular-nums">
                  {formatAmount(part.total)} {part.currency}
                </span>
              </p>
            </section>
          ))}

          {perDiem.parts.some((part) => part.currency !== "PLN") && (
            <div className="flex flex-col gap-0.5 rounded-control bg-muted px-3 py-2.5">
              <p className="m-0 flex items-baseline justify-between gap-3 text-md font-bold">
                <span>{t("perDiem.totalPln")}</span>
                <span className="tabular-nums">
                  {perDiem.total_pln ? `${formatAmount(perDiem.total_pln)} PLN` : "—"}
                </span>
              </p>
              {perDiem.to_pln.map((rate) => (
                <span key={rate.currency} className="text-base text-muted-foreground">
                  {rate.rate && rate.effective_date
                    ? `${rate.currency} ${t("perDiem.rate", {
                        rate: RATE.format(Number(rate.rate)),
                        date: RATE_DAY.format(new Date(`${rate.effective_date}T00:00:00Z`)),
                      })}`
                    : t("perDiem.noRate")}
                </span>
              ))}
            </div>
          )}

          <p className="m-0 text-base text-muted-foreground">
            {t("perDiem.regulation", { act: perDiem.regulation })}
          </p>
        </>
      )}

      {editing && (
        <PerDiemDialog
          trip={trip}
          onClose={() => {
            setEditing(false);
          }}
        />
      )}
    </Card>
  );
});
