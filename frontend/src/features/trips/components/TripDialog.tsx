import { useId, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import {
  Button,
  Input,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  SegmentedControl,
  Select,
} from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { TripRequest } from "@/stores/TripsStore";
import { countryOptions } from "../tripFormat";

type TripKind = TripRequest["kind"];

/**
 * Recording a trip, or changing one (F20.1).
 *
 * `initial` prefills it — a trip being changed, or a suggested one. The dates are
 * inclusive; the server refuses a trip that overlaps another, and its message is
 * shown here. Calls `onSaved` with the trip's id once saved.
 */
export const TripDialog = observer(function TripDialog({
  initial,
  tripId,
  onClose,
  onSaved,
}: {
  initial?: Partial<TripRequest>;
  tripId?: string;
  onClose: () => void;
  onSaved?: (id: string) => void;
}) {
  const { tripsStore } = useStores();
  const { t } = useTranslation(["trips", "common"]);
  const titleId = useId();
  const [kind, setKind] = useState<TripKind>(initial?.kind ?? "personal");
  const [name, setName] = useState(initial?.name ?? "");
  const [country, setCountry] = useState(initial?.country ?? "");
  const [city, setCity] = useState(initial?.city ?? "");
  const [start, setStart] = useState(initial?.start_date ?? "");
  const [end, setEnd] = useState(initial?.end_date ?? "");
  const [purpose, setPurpose] = useState(initial?.purpose ?? "");
  const [countries] = useState(countryOptions);

  const endBeforeStart = Boolean(start && end && end < start);
  const ready = name.trim() !== "" && start !== "" && end !== "" && !endBeforeStart;

  const close = () => {
    tripsStore.clearSaveError();
    onClose();
  };

  const save = async () => {
    if (!ready) return;
    const id = await tripsStore.save(
      {
        kind,
        name: name.trim(),
        country: country || null,
        city: city.trim() || null,
        start_date: start,
        end_date: end,
        purpose: kind === "business" ? purpose.trim() || null : null,
      },
      tripId,
    );
    if (id) {
      onSaved?.(id);
      close();
    }
  };

  return (
    <Modal isOpen onClose={close} aria-labelledby={titleId} className="md:w-[520px]">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <ModalHeader>
          <h2 id={titleId} className="m-0 text-[17px] font-bold">
            {t(tripId ? "form.editTitle" : "form.newTitle")}
          </h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1.5">
            <SegmentedControl<TripKind>
              label={t("form.kind")}
              fill
              value={kind}
              onChange={setKind}
              options={[
                { value: "personal", label: t("kind.personal") },
                { value: "business", label: t("kind.business") },
              ]}
            />
            <p className="m-0 text-base text-muted-foreground">{t(`kindHint.${kind}`)}</p>
          </div>
          <Input
            label={t("form.name")}
            value={name}
            maxLength={80}
            placeholder={t("form.namePlaceholder")}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
          <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
            <Select
              label={t("form.country")}
              value={country}
              onChange={(e) => {
                setCountry(e.target.value);
              }}
            >
              <option value="">{t("form.noCountry")}</option>
              {countries.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.name}
                </option>
              ))}
            </Select>
            <Input
              label={t("form.city")}
              value={city}
              maxLength={80}
              onChange={(e) => {
                setCity(e.target.value);
              }}
            />
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <Input
              type="date"
              label={t("form.start")}
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
              }}
            />
            <Input
              type="date"
              label={t("form.end")}
              value={end}
              min={start || undefined}
              error={endBeforeStart ? t("form.endBeforeStart") : undefined}
              onChange={(e) => {
                setEnd(e.target.value);
              }}
            />
          </div>
          {kind === "business" && (
            <Input
              label={t("form.purpose")}
              value={purpose}
              maxLength={200}
              placeholder={t("form.purposePlaceholder")}
              onChange={(e) => {
                setPurpose(e.target.value);
              }}
            />
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
            <Button type="submit" variant="primary" disabled={!ready || tripsStore.isSaving}>
              {t("form.save")}
            </Button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
});
