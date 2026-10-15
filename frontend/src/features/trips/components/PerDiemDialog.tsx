import { useId, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, ModalFooter, ModalHeader } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { Meal, TripDetail } from "@/stores/TripsStore";
import { dayCount, fromLocalInput, toLocalInput } from "../perDiem";

const MEALS: Meal[] = ["breakfast", "lunch", "dinner"];

/**
 * A business trip's times and the meals provided each day, for its per diem (F20.4).
 *
 * A trip abroad may give the border times too (§ 12); without them it counts as abroad
 * throughout. The meals are asked for each 24-hour day of the time abroad — or of the
 * whole trip, for one in Poland — as the regulation counts days, from the departure.
 */
export const PerDiemDialog = observer(function PerDiemDialog({
  trip,
  onClose,
}: {
  trip: TripDetail;
  onClose: () => void;
}) {
  const { tripsStore } = useStores();
  const { t } = useTranslation(["trips", "common"]);
  const titleId = useId();
  const given = trip.per_diem;
  const abroad = Boolean(trip.country && trip.country !== "PL");
  const [departure, setDeparture] = useState(
    given ? toLocalInput(given.departure) : `${trip.start_date}T08:00`,
  );
  const [returned, setReturned] = useState(
    given ? toLocalInput(given.returned) : `${trip.end_date}T18:00`,
  );
  const [crossed, setCrossed] = useState(Boolean(given?.abroad_from));
  const [abroadFrom, setAbroadFrom] = useState(
    given?.abroad_from ? toLocalInput(given.abroad_from) : departure,
  );
  const [abroadTo, setAbroadTo] = useState(
    given?.abroad_to ? toLocalInput(given.abroad_to) : returned,
  );
  const [meals, setMeals] = useState<Meal[][]>(given?.meals ?? []);

  const days = abroad && crossed ? dayCount(abroadFrom, abroadTo) : dayCount(departure, returned);
  const inOrder = dayCount(departure, returned) > 0;

  const mealsOf = (day: number): Meal[] => meals[day] ?? [];

  const toggle = (day: number, meal: Meal) => {
    const next: Meal[][] = Array.from({ length: days }, (_, i) => mealsOf(i));
    const current = mealsOf(day);
    next[day] = current.includes(meal) ? current.filter((m) => m !== meal) : [...current, meal];
    setMeals(next);
  };

  const close = () => {
    tripsStore.clearSaveError();
    onClose();
  };

  const save = async () => {
    const saved = await tripsStore.setTimes(trip.id, {
      departure: fromLocalInput(departure),
      returned: fromLocalInput(returned),
      abroad_from: abroad && crossed ? fromLocalInput(abroadFrom) : null,
      abroad_to: abroad && crossed ? fromLocalInput(abroadTo) : null,
      meals: Array.from({ length: days }, (_, i) => mealsOf(i)),
    });
    if (saved) close();
  };

  return (
    <Modal isOpen onClose={close} aria-labelledby={titleId} className="md:w-[560px]">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <ModalHeader>
          <h2 id={titleId} className="m-0 text-[17px] font-bold">
            {t("perDiem.dialog.title")}
          </h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-3.5">
          <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
            <Input
              type="datetime-local"
              label={t("perDiem.dialog.departure")}
              value={departure}
              onChange={(e) => {
                setDeparture(e.target.value);
              }}
            />
            <Input
              type="datetime-local"
              label={t("perDiem.dialog.returned")}
              value={returned}
              min={departure}
              error={inOrder ? undefined : t("perDiem.dialog.order")}
              onChange={(e) => {
                setReturned(e.target.value);
              }}
            />
          </div>
          {abroad && (
            <label className="flex min-h-11 cursor-pointer items-center gap-3 text-md">
              <input
                type="checkbox"
                checked={crossed}
                onChange={(e) => {
                  setCrossed(e.target.checked);
                }}
                className="h-5 w-5 shrink-0 cursor-pointer accent-primary"
              />
              {t("perDiem.dialog.crossed")}
            </label>
          )}
          {abroad && crossed && (
            <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
              <Input
                type="datetime-local"
                label={t("perDiem.dialog.abroadFrom")}
                value={abroadFrom}
                onChange={(e) => {
                  setAbroadFrom(e.target.value);
                }}
              />
              <Input
                type="datetime-local"
                label={t("perDiem.dialog.abroadTo")}
                value={abroadTo}
                onChange={(e) => {
                  setAbroadTo(e.target.value);
                }}
              />
            </div>
          )}
          {days > 0 && (
            <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
              <legend className="mb-1 p-0 text-base font-medium text-muted-foreground">
                {t("perDiem.dialog.mealsTitle")}
              </legend>
              <p className="m-0 text-base text-muted-foreground">{t("perDiem.dialog.mealsHint")}</p>
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {Array.from({ length: days }, (_, day) => (
                  <li
                    key={day}
                    className="flex flex-col gap-1.5 md:flex-row md:items-center md:justify-between"
                  >
                    <span className="text-md font-semibold">
                      {t("perDiem.day", { number: day + 1 })}
                    </span>
                    <span
                      role="group"
                      aria-label={t("perDiem.day", { number: day + 1 })}
                      className="flex gap-1.5 [&>*]:flex-1 md:[&>*]:flex-none"
                    >
                      {MEALS.map((meal) => {
                        const on = mealsOf(day).includes(meal);
                        return (
                          <button
                            key={meal}
                            type="button"
                            aria-pressed={on}
                            onClick={() => {
                              toggle(day, meal);
                            }}
                            className={`min-h-11 cursor-pointer rounded-control border px-3 text-md transition-colors md:min-h-9 ${
                              on
                                ? "border-primary bg-primary/10 font-semibold text-primary"
                                : "border-border bg-background text-foreground hover:bg-surface-hover"
                            }`}
                          >
                            {t(`perDiem.meal.${meal}`)}
                          </button>
                        );
                      })}
                    </span>
                  </li>
                ))}
              </ul>
            </fieldset>
          )}
          {tripsStore.saveError && (
            <p role="alert" className="m-0 text-base text-error">
              {tripsStore.saveError}
            </p>
          )}
        </ModalBody>
        <ModalFooter>
          <span className="hidden md:block" />
          <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
            <Button type="button" variant="ghost" onClick={close}>
              {t("common:cancel")}
            </Button>
            <Button type="submit" disabled={!inOrder || tripsStore.isSaving}>
              {t("perDiem.dialog.save")}
            </Button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
});
