import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";

import { PALETTES, type Palette } from "@/stores/ThemeStore";

export interface PalettePickerProps {
  value: Palette;
  onChange: (palette: Palette) => void;
  label: string;
}

/**
 * The six palettes as tiles, each painted in its own colours (F23.1): a tile carries the
 * palette's attribute, so the tokens inside it are that palette's.
 */
export function PalettePicker({ value, onChange, label }: PalettePickerProps) {
  const { t } = useTranslation("profile");
  return (
    <div role="radiogroup" aria-label={label} className="grid grid-cols-2 gap-2.5 md:grid-cols-3">
      {PALETTES.map(({ id, dark }) => {
        const chosen = value === id;
        return (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={chosen}
            data-palette={id}
            onClick={() => {
              onChange(id);
            }}
            className={`${dark ? "dark" : ""} flex min-h-24 flex-col justify-between gap-3 rounded-card border-2 bg-muted p-3 text-left text-foreground transition-transform active:scale-[0.98] ${
              chosen ? "border-primary" : "border-border"
            }`}
          >
            <span className="flex items-center gap-1.5" aria-hidden="true">
              <span className="h-5.5 w-5.5 rounded-pill bg-primary" />
              <span className="h-5.5 w-5.5 rounded-pill bg-[var(--cat-dining)]" />
              <span className="h-5.5 w-5.5 rounded-pill bg-[var(--cat-transport)]" />
              <span className="h-5.5 w-5.5 rounded-pill bg-[var(--cat-utilities)]" />
            </span>
            <span className="flex items-center justify-between gap-2">
              <span className="text-lg font-bold">{t(`appearance.palettes.${id}`)}</span>
              {chosen && <Check size={18} className="text-primary" aria-hidden="true" />}
            </span>
          </button>
        );
      })}
    </div>
  );
}
