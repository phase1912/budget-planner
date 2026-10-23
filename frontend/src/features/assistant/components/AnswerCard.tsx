import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import type { components } from "@/api/schema";
import { CategoryChart } from "@/shared/components";
import { periodLabel } from "@/features/statistics/periodLabel";
import type { ChatMessage } from "@/stores/AssistantStore";
import { AccountsDrawing, GoalsDrawing, MonthDrawing, ProductsDrawing } from "./AnswerDrawings";

type Chart = components["schemas"]["ChartResponse"];

const SCREENS = [
  "spending",
  "receipts",
  "products",
  "accounts",
  "home",
  "month",
  "goals",
  "settings",
] as const;
type Screen = (typeof SCREENS)[number];

const day = (value: unknown): string | null =>
  typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null;

function isChart(value: unknown): value is Chart {
  return typeof value === "object" && value !== null && "groups" in value && "ticks" in value;
}

function isScreen(value: unknown): value is Screen {
  return SCREENS.some((screen) => screen === value);
}

/**
 * What an answer came with, drawn the way its screen draws it (F21.4, F21.14): the chart of
 * spending by category, the cards with their balances, the month as Home's ring, each goal
 * with its bar, products as rows — and a link to the screen holding the full figures with
 * the same filters. Nothing to approve: it only shows what the read found.
 */
export function AnswerCard({ message }: { message: ChatMessage }) {
  const { t } = useTranslation("assistant");
  const fields = message.card?.fields ?? {};
  const to = typeof fields.to === "string" && fields.to.startsWith("/") ? fields.to : null;
  const [start, end] = [day(fields.start), day(fields.end)];
  const [previousStart, previousEnd] = [day(fields.previous_start), day(fields.previous_end)];
  const chart = isChart(fields.chart) && start && end ? fields.chart : null;

  return (
    <div className="flex flex-col gap-2">
      {chart && start && end && (
        <CategoryChart
          chart={chart}
          current={periodLabel(start, end)}
          previous={previousStart && previousEnd ? periodLabel(previousStart, previousEnd) : null}
          hiddenNote={(count) => t("answer.hidden", { count })}
        />
      )}
      {fields.screen === "accounts" && <AccountsDrawing fields={fields} />}
      {fields.screen === "month" && <MonthDrawing fields={fields} />}
      {fields.screen === "goals" && <GoalsDrawing fields={fields} />}
      {fields.screen === "products" && <ProductsDrawing fields={fields} />}
      {to && isScreen(fields.screen) && (
        <Link
          to={to}
          className="inline-flex min-h-11 items-center gap-2 self-start rounded-pill bg-tone-primary-bg px-4 text-md font-bold text-primary no-underline"
        >
          {t(`answer.${fields.screen}`)}
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
