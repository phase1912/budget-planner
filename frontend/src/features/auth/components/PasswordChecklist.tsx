import { Check, X } from "lucide-react";

import { PASSWORD_RULES } from "../passwordRules";
import { useTranslation } from "react-i18next";

/**
 * Each password rule ticked off as it is met, and whether the two passwords match
 * (BRD G1): what a refusal would say, shown before anyone presses Register.
 */
export function PasswordChecklist({ password, confirm }: { password: string; confirm: string }) {
  const { t } = useTranslation("auth");
  const checks = [
    ...PASSWORD_RULES.map((rule) => ({
      label: t(`password.${rule.label}`),
      met: rule.met(password),
    })),
    { label: t("password.match"), met: confirm !== "" && password === confirm },
  ];
  return (
    <ul aria-label={t("password.needs")} className="m-0 flex list-none flex-col gap-1.5 p-0">
      {checks.map(({ label, met }) => (
        <li
          key={label}
          className={`flex items-center gap-2 text-md ${met ? "text-tone-primary-text" : "text-muted-foreground"}`}
        >
          {met ? (
            <Check size={15} aria-hidden="true" className="shrink-0" />
          ) : (
            <X size={15} aria-hidden="true" className="shrink-0" />
          )}
          <span>
            {label}
            <span className="sr-only">{met ? t("password.done") : t("password.missing")}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
