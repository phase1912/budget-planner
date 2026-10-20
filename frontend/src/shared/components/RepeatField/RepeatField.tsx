import { useTranslation } from "react-i18next";

import { type Repeat, weekdayName } from "./repeat";
import { SegmentedControl } from "../SegmentedControl/SegmentedControl";
import { Select } from "../Select/Select";

const DAYS = Array.from({ length: 30 }, (_, i) => i + 1);

/**
 * When a regular bill or income comes (F23.21): monthly on a day, or weekly on a weekday —
 * a weekly one counts as often as its day falls in each month.
 */
export function RepeatField({
  value,
  onChange,
}: {
  value: Repeat;
  onChange: (value: Repeat) => void;
}) {
  const { t } = useTranslation();
  const weekly = value.weekday !== null;
  return (
    <div className="flex flex-col gap-3">
      <SegmentedControl<"month" | "week">
        label={t("repeat.label")}
        size="sm"
        fill
        value={weekly ? "week" : "month"}
        onChange={(every) => {
          onChange(every === "week" ? { day: null, weekday: 0 } : { day: null, weekday: null });
        }}
        options={[
          { value: "month", label: t("repeat.monthly") },
          { value: "week", label: t("repeat.weekly") },
        ]}
      />
      {weekly ? (
        <Select
          label={t("repeat.weekday")}
          value={String(value.weekday)}
          onChange={(e) => {
            onChange({ day: null, weekday: Number(e.target.value) });
          }}
        >
          {[0, 1, 2, 3, 4, 5, 6].map((i) => (
            <option key={i} value={i}>
              {weekdayName(i)}
            </option>
          ))}
        </Select>
      ) : (
        <Select
          label={t("repeat.day")}
          value={value.day === null ? "" : String(value.day)}
          onChange={(e) => {
            onChange({ day: e.target.value ? Number(e.target.value) : null, weekday: null });
          }}
        >
          <option value="">{t("repeat.anyDay")}</option>
          {DAYS.map((day) => (
            <option key={day} value={day}>
              {day}
            </option>
          ))}
          <option value="31">{t("repeat.lastDay")}</option>
        </Select>
      )}
    </div>
  );
}
