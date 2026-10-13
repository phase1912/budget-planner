import { useEffect, useId, useRef, useState } from "react";
import { observer } from "mobx-react-lite";

import { Button, Input } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { Trans, useTranslation } from "react-i18next";

/** "37", "37.5", "37,50", "1 214,60": what people type for an amount. */
const AMOUNT = /^\d[\d\s]*([.,]\d{1,2})?$/;

interface ResolveTotalFormProps {
  extractionIndex: number;
  /** The sum of the lines the parser read: offered as the likely answer. */
  computedTotal: string | null | undefined;
  lineCount: number;
  /** Put the cursor in the field; true when the user just asked to enter a total. */
  autoFocusField?: boolean;
}

/**
 * Supplies the printed total of a receipt the parser could not read (BRD A11).
 *
 * The lines' sum is offered first, one click to accept, and prefilled in the
 * field: on most receipts the printed total is exactly that, and typing it
 * again invites a typo. Used on both the "What we read" and "Resolve" steps.
 */
export const ResolveTotalForm = observer(function ResolveTotalForm({
  extractionIndex,
  computedTotal,
  lineCount,
  autoFocusField = false,
}: ResolveTotalFormProps) {
  const { uploadStore } = useStores();
  const { t } = useTranslation("upload");
  const fieldId = useId();
  const field = useRef<HTMLInputElement>(null);
  const [total, setTotal] = useState(computedTotal ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const typed = total.trim();
  const invalid = typed !== "" && !AMOUNT.test(typed);

  useEffect(() => {
    if (autoFocusField) field.current?.focus();
  }, [autoFocusField]);

  const save = async (value: string) => {
    if (!AMOUNT.test(value.trim()) || isSaving) return;
    setIsSaving(true);
    await uploadStore.resolveTotal(extractionIndex, value.trim());
    setIsSaving(false);
  };

  return (
    <form
      className="flex flex-col gap-2.5"
      onSubmit={(e) => {
        e.preventDefault();
        void save(total);
      }}
    >
      {computedTotal && (
        <p className="m-0 text-md text-muted-foreground">
          <Trans
            t={t}
            i18nKey="total.linesAdd"
            count={lineCount}
            values={{ total: computedTotal }}
            components={{ b: <span className="tabular-nums font-semibold text-foreground" /> }}
          />
        </p>
      )}
      <div className="flex flex-wrap items-start gap-2.5">
        {computedTotal && (
          <>
            <Button
              type="button"
              size="sm"
              disabled={isSaving}
              onClick={() => {
                void save(computedTotal);
              }}
            >
              {t("total.right", { total: computedTotal })}
            </Button>
            <span className="py-2 text-md text-muted-foreground">{t("total.or")}</span>
          </>
        )}
        <div className="w-40">
          <Input
            ref={field}
            id={fieldId}
            aria-label={t("total.printed")}
            inputMode="decimal"
            placeholder="0.00"
            className="w-full py-2 text-md tabular-nums"
            error={invalid ? t("total.invalid") : undefined}
            value={total}
            onChange={(e) => {
              setTotal(e.target.value);
            }}
          />
        </div>
        <Button
          type="submit"
          variant="secondary"
          size="sm"
          disabled={!typed || invalid || isSaving}
        >
          {t("total.save")}
        </Button>
      </div>
    </form>
  );
});
