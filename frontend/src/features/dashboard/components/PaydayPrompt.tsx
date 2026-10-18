import { Banknote } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components";
import { numberFormat } from "@/i18n/format";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });

interface PaydayPromptProps {
  usual: string;
  currency: string;
  busy: boolean;
  onConfirm: () => void;
  onOther: () => void;
}

/**
 * Payday has come and the month has no income entered (F23.10): one tap records the usual
 * salary as received today, or another amount when it differed. Until then the usual
 * amount only stands in, so the balance would not move.
 */
export function PaydayPrompt({ usual, currency, busy, onConfirm, onOther }: PaydayPromptProps) {
  const { t } = useTranslation("dashboard");
  return (
    <section
      aria-label={t("payday.question")}
      className="flex flex-col gap-3 rounded-card bg-tone-primary-bg px-4 py-3.5"
    >
      <span className="flex items-center gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-primary text-primary-foreground">
          <Banknote size={20} aria-hidden="true" />
        </span>
        <span className="flex flex-col">
          <span className="text-lg font-bold">{t("payday.question")}</span>
          <span className="text-xl font-extrabold tabular-nums">
            {WHOLE.format(Number(usual))} {currency}
          </span>
        </span>
      </span>
      <span className="grid grid-cols-2 gap-2">
        <Button size="sm" className="min-h-11" disabled={busy} onClick={onConfirm}>
          {t("payday.yes")}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          className="min-h-11"
          disabled={busy}
          onClick={onOther}
        >
          {t("payday.other")}
        </Button>
      </span>
    </section>
  );
}
