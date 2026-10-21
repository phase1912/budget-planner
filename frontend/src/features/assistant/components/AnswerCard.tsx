import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import type { components } from "@/api/schema";
import { CategoryChart } from "@/shared/components";
import { periodLabel } from "@/features/statistics/periodLabel";
import type { ChatMessage } from "@/stores/AssistantStore";

type Chart = components["schemas"]["ChartResponse"];

const SCREENS = ["spending", "receipts", "products", "accounts", "home"] as const;
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
 * What an answer about spending came with (F21.4): the chart the Spending screen would draw
 * for that period, and a link to the screen holding the full figures with the same
 * filters — Spending, Receipts or a product's prices. Nothing to approve: it only shows.
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
