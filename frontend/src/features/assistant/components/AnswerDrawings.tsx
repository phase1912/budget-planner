import { useTranslation } from "react-i18next";

import { Meter, Pill, Ring } from "@/shared/components";
import { numberFormat } from "@/i18n/format";

const MONEY = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });

type Fields = Record<string, unknown>;

const rows = (value: unknown): Fields[] =>
  Array.isArray(value) ? value.filter((v): v is Fields => typeof v === "object" && v !== null) : [];
const text = (value: unknown): string =>
  typeof value === "string" || typeof value === "number" ? String(value) : "";
const amount = (value: unknown, currency: string): string =>
  `${MONEY.format(Number(text(value) || 0))} ${currency}`;

/** The cards an answer is about, as the Accounts screen shows them (F21.14). */
export function AccountsDrawing({ fields }: { fields: Fields }) {
  const { t } = useTranslation("assistant");
  const currency = text(fields.currency);
  const accounts = rows(fields.accounts);
  if (accounts.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <ul className="m-0 grid list-none grid-cols-1 gap-2 p-0 md:grid-cols-2">
        {accounts.map((a) => (
          <li
            key={text(a.name)}
            className="flex flex-col gap-1 rounded-card border border-border bg-surface px-4 py-3"
          >
            <span className="flex flex-wrap items-center gap-2 text-md font-bold">
              <span className="min-w-0 break-words">{text(a.name)}</span>
              {a.pays_for_purchases === true && (
                <Pill size="sm" tone="success">
                  {t("answer.paysForPurchases")}
                </Pill>
              )}
            </span>
            <span className="text-base text-muted-foreground">
              {a.kind === "business"
                ? t("card.options.business")
                : a.kind === "deposit"
                  ? t("card.options.deposit")
                  : t("card.options.personal")}
            </span>
            <span
              className={`text-xl font-extrabold tabular-nums ${Number(text(a.balance)) < 0 ? "text-tone-error-text" : ""}`}
            >
              {amount(a.balance, currency)}
            </span>
          </li>
        ))}
      </ul>
      {accounts.length > 1 && (
        <p className="m-0 text-md text-muted-foreground tabular-nums">
          {t("answer.total", { amount: amount(fields.total, currency) })}
        </p>
      )}
    </div>
  );
}

/** The month as Home's ring draws it: bills, then what was spent, against the budget. */
export function MonthDrawing({ fields }: { fields: Fields }) {
  const { t } = useTranslation("assistant");
  const currency = text(fields.currency);
  const spent = Number(text(fields.spent) || 0);
  const bills = Number(text(fields.bills) || 0);
  const budget = fields.budget == null ? null : Number(text(fields.budget));
  const left = budget === null ? null : budget - bills - spent;
  const over = left !== null && left < 0;
  return (
    <div className="flex items-center gap-4 rounded-card border border-border bg-surface p-4">
      <Ring
        className="h-24 w-24 shrink-0"
        max={budget ?? spent + bills}
        segments={[
          { value: bills, color: "var(--cat-utilities)" },
          { value: spent, color: over ? "var(--color-error)" : "var(--color-primary)" },
        ]}
        label={t("answer.ring", {
          spent: amount(spent, currency),
          bills: amount(bills, currency),
        })}
      />
      <dl className="m-0 grid min-w-0 grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-md tabular-nums">
        <dt className="text-muted-foreground">{t("answer.spent")}</dt>
        <dd className="m-0 font-bold">{amount(spent, currency)}</dd>
        <dt className="text-muted-foreground">{t("answer.bills")}</dt>
        <dd className="m-0 font-bold">{amount(bills, currency)}</dd>
        {left !== null && (
          <>
            <dt className="text-muted-foreground">
              {over ? t("answer.overBudget") : t("answer.leftOfBudget")}
            </dt>
            <dd className={`m-0 font-bold ${over ? "text-tone-error-text" : ""}`}>
              {amount(Math.abs(left), currency)}
            </dd>
          </>
        )}
      </dl>
    </div>
  );
}

/** Each goal with its bar, as the Goals screen leads its cards (F8.11.2). */
export function GoalsDrawing({ fields }: { fields: Fields }) {
  const { t } = useTranslation("assistant");
  const currency = text(fields.currency);
  const goals = rows(fields.goals);
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {goals.map((g) => {
        const lifestyle = g.measure === "lifestyle";
        const percent = Number(text(g.percent) || 0);
        const late = g.overdue === true || g.on_track === false;
        return (
          <li
            key={text(g.name)}
            className="flex flex-col gap-1.5 rounded-card border border-border bg-surface px-4 py-3"
          >
            <span className="flex items-baseline justify-between gap-2">
              <span className="min-w-0 break-words text-md font-bold">{text(g.name)}</span>
              {!lifestyle && (
                <span className="shrink-0 text-md font-bold tabular-nums">{percent}%</span>
              )}
            </span>
            {!lifestyle && <Meter value={percent} tone={late ? "error" : "primary"} />}
            <span className="text-base text-muted-foreground tabular-nums">
              {g.measure === "savings"
                ? t("answer.goalSaved", {
                    saved: amount(g.saved, currency),
                    target: amount(g.target, currency),
                  })
                : g.measure === "month"
                  ? t("answer.goalMonth", {
                      spent: amount(g.spent_this_month, currency),
                      target: amount(g.target, currency),
                    })
                  : t("answer.goalLifestyle", {
                      amount: amount(g.this_month, currency),
                      usual: amount(g.monthly_average, currency),
                    })}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Products an answer found, a row each: how often bought, and what it cost. */
export function ProductsDrawing({ fields }: { fields: Fields }) {
  const { t } = useTranslation("assistant");
  const currency = text(fields.currency);
  const products = rows(fields.products);
  if (products.length === 0) return null;
  return (
    <ul className="m-0 flex list-none flex-col divide-y divide-border rounded-card border border-border bg-surface p-0">
      {products.map((p) => (
        <li key={text(p.name)} className="flex items-center justify-between gap-3 px-4 py-2.5">
          <span className="flex min-w-0 flex-col">
            <span className="break-words text-md font-semibold">{text(p.name)}</span>
            <span className="text-base text-muted-foreground tabular-nums">
              {t("answer.receipts", { count: Number(text(p.receipts) || 0) })}
            </span>
          </span>
          <span className="shrink-0 text-md font-bold tabular-nums">
            {p.a_month != null
              ? t("answer.aMonth", { amount: amount(p.a_month, currency) })
              : amount(p.spent, currency)}
          </span>
        </li>
      ))}
    </ul>
  );
}
