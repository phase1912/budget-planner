import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { dateFormat, numberFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";
import { memberColours } from "../memberColours";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAY = dateFormat({ day: "numeric", month: "short" });
const LONG_DAY = dateFormat({ day: "numeric", month: "long" });

const asDate = (day: string) => new Date(`${day}T00:00:00`);

/**
 * The household's spending day by day (F12.5, F23.4): a bar a day, stacked by member,
 * the viewer at the bottom in the primary colour. Tapping a bar names each member's share
 * of that day. The other members' private spending has no day (ADR-0017), so it is
 * named beneath as one sum rather than left out silently.
 */
export const HouseholdDailyBars = observer(function HouseholdDailyBars({
  currency,
  today,
  bare = false,
}: {
  currency: string;
  today: string;
  /** Inside another card (the family Home): no card or title of its own. */
  bare?: boolean;
}) {
  const { householdStore, authStore } = useStores();
  const { t } = useTranslation("household");
  const [chosen, setChosen] = useState<string | null>(null);
  const daily = householdStore.daily;
  if (!daily || daily.days.length === 0 || daily.days.length > 62) return null;

  const me = authStore.user?.id;
  const members = [...daily.members].sort(
    (a, b) => Number(b.user_id === me) - Number(a.user_id === me),
  );
  const colourOf = memberColours(
    members.map((m) => m.user_id),
    me,
  );
  const nameOf = (id: string) =>
    id === me ? t("daily.you") : (members.find((m) => m.user_id === id)?.first_name ?? "");
  const dayTotal = (d: (typeof daily.days)[number]) =>
    d.members.reduce((sum, m) => sum + Number(m.total), 0);
  const peak = Math.max(...daily.days.map(dayTotal), 0);
  const passed = daily.days.filter((d) => d.day <= today);
  const selected =
    daily.days.find((d) => d.day === chosen) ??
    passed.filter((d) => dayTotal(d) > 0).pop() ??
    passed[passed.length - 1] ??
    daily.days[0];
  const totalOf = (id: string) =>
    daily.days.reduce(
      (sum, d) => sum + Number(d.members.find((m) => m.user_id === id)?.total ?? 0),
      0,
    );
  const ordered = (d: (typeof daily.days)[number]) =>
    members.map((m) => ({
      id: m.user_id,
      total: Number(d.members.find((x) => x.user_id === m.user_id)?.total ?? 0),
    }));

  return (
    <section
      aria-label={t("daily.title")}
      className={
        bare ? "flex flex-col gap-3" : "flex flex-col gap-3 rounded-card bg-surface p-4 md:p-5"
      }
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        {!bare && <h2 className="m-0 text-xl font-extrabold">{t("daily.title")}</h2>}
        {selected && (
          <span className="text-md font-bold tabular-nums" aria-live="polite">
            {DAY.format(asDate(selected.day))} ·{" "}
            {ordered(selected)
              .filter((m) => m.total > 0)
              .map((m) => `${nameOf(m.id)} ${WHOLE.format(m.total)}`)
              .join(" · ") || WHOLE.format(0)}{" "}
            {currency}
          </span>
        )}
      </div>
      <div className="flex h-30 items-end gap-0.5 md:gap-1">
        {daily.days.map((d) => {
          const total = dayTotal(d);
          const isSelected = d.day === selected?.day;
          return (
            <button
              key={d.day}
              type="button"
              aria-pressed={isSelected}
              aria-label={t("daily.bar", {
                date: LONG_DAY.format(asDate(d.day)),
                amounts: ordered(d)
                  .map((m) => `${nameOf(m.id)} ${WHOLE.format(m.total)}`)
                  .join(", "),
                currency,
              })}
              onClick={() => {
                setChosen(d.day);
              }}
              className="flex h-full min-w-0 flex-1 items-end"
            >
              <span
                className={`flex w-full flex-col-reverse overflow-hidden rounded-t-[5px] rounded-b-[2px] ${
                  total === 0 ? "bg-tone-primary-bg" : ""
                } ${isSelected || chosen === null ? "" : "opacity-60"}`}
                style={{ height: `${String(Math.max(4, peak > 0 ? (total / peak) * 100 : 0))}%` }}
              >
                {total > 0 &&
                  ordered(d).map((m) => (
                    <span
                      key={m.id}
                      className="block w-full"
                      style={{
                        height: `${String((m.total / total) * 100)}%`,
                        background: colourOf.get(m.id),
                      }}
                    />
                  ))}
              </span>
            </button>
          );
        })}
      </div>
      <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1.5 p-0">
        {members.map((m) => (
          <li key={m.user_id} className="flex items-center gap-2 text-md">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 shrink-0 rounded-pill"
              style={{ background: colourOf.get(m.user_id) }}
            />
            <span className="font-semibold">{nameOf(m.user_id)}</span>
            <span className="text-muted-foreground tabular-nums">
              {WHOLE.format(totalOf(m.user_id))} {currency}
            </span>
          </li>
        ))}
      </ul>
      {Number(daily.undated_private) > 0 && (
        <p className="m-0 text-md text-muted-foreground tabular-nums">
          {t("daily.undatedPrivate", {
            amount: WHOLE.format(Number(daily.undated_private)),
            currency,
          })}
        </p>
      )}
    </section>
  );
});
