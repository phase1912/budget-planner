import { Briefcase, CreditCard, PiggyBank, type LucideIcon } from "lucide-react";

import { numberFormat } from "@/i18n/format";
import type { AccountKind, BankAccount } from "@/stores/BankAccountsStore";

export const WHOLE = numberFormat({ maximumFractionDigits: 0 });
export const COMMON_RATES = ["5", "6", "12"] as const;

/** The icon an account carries in lists, by what it is for. */
export const KIND_ICON: Record<AccountKind, LucideIcon> = {
  personal: CreditCard,
  business: Briefcase,
  deposit: PiggyBank,
};

/** A rate as typed or stored ("5.00"), shown without trailing zeros ("5"). */
export function rateText(rate: string | null | undefined): string {
  return rate == null ? "" : String(Number(rate));
}

/** Which locale key describes the account under its name. */
export function kindLineKey(
  account: Pick<BankAccount, "kind" | "tax_rate">,
): `kindLine.${"personal" | "business" | "businessNoTax" | "deposit"}` {
  if (account.kind === "business") {
    return Number(account.tax_rate ?? 0) > 0 ? "kindLine.business" : "kindLine.businessNoTax";
  }
  return `kindLine.${account.kind}`;
}

/** An amount typed by a person — "1 600,50" — as the API wants it, or null when it is not one. */
export function typedAmount(text: string): string | null {
  const plain = text.trim().replace(",", ".").replace(/\s/g, "");
  return /^\d+(\.\d{1,2})?$/.test(plain) ? plain : null;
}

/**
 * The day a monthly rule made today first runs (F23.15): this month on `day`, or — when
 * that day has already passed — the same day next month; a 31st means a month's last day.
 */
export function firstRun(day: number | null, today: Date): { date: Date; nextMonth: boolean } {
  const onDay = (year: number, month: number) => {
    const last = new Date(year, month + 1, 0).getDate();
    return new Date(year, month, Math.min(day ?? 1, last));
  };
  const thisMonth = onDay(today.getFullYear(), today.getMonth());
  if (day === null || thisMonth.getDate() >= today.getDate()) {
    return { date: day === null ? today : thisMonth, nextMonth: false };
  }
  return { date: onDay(today.getFullYear(), today.getMonth() + 1), nextMonth: true };
}
