import type { ReactNode } from "react";
import { Heart, Pencil, Plus, Target } from "lucide-react";

import { Card, IconButton, IconTile, Pill } from "@/shared/components";
import type { Goal } from "@/stores/GoalsStore";
import { metaOf } from "../goalKinds";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const SET_ON = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric" });

interface GoalCardProps {
  goal: Goal;
  currency: string;
  /** A category's name by id, when known: the one a reduction cuts, the ones a goal watches. */
  categoryName: (id: string | null | undefined) => string | null;
  onEdit: () => void;
  /** What follows the goal itself at the foot of the card: its advice (F8.4). */
  children?: ReactNode;
}

/** What a money goal asks for, in words: "Stay under 3,000.00 PLN a month". */
function target(goal: Goal, currency: string, categoryName: string | null): string {
  const amount = `${AMOUNT.format(Number(goal.target_amount))} ${currency}`;
  switch (goal.financial_kind) {
    case "savings_target":
      return `Put ${amount} aside`;
    case "category_reduction":
      return `Keep ${categoryName ?? "a removed category"} under ${amount} a month`;
    default:
      return `Stay under ${amount} a month`;
  }
}

/**
 * One goal as docs/design/screens/goals.html shows it (BRD F1 — F8.1): what it is,
 * when it was set, and what it asks for. A lifestyle goal is read through the
 * things bought, so it lists the categories and items it watches (F8.2), with a
 * way to adjust them. Its advice (F8.4) sits at the foot of the card, where it is
 * asked for; progress arrives with later E8 features.
 */
export function GoalCard({ goal, currency, categoryName, onEdit, children }: GoalCardProps) {
  const lifestyle = goal.type === "lifestyle";
  const Icon = lifestyle ? Heart : Target;
  const watched = [
    ...goal.mapped_category_ids.map((id) => categoryName(id)).filter((n): n is string => !!n),
    ...goal.mapped_item_names,
  ];
  return (
    <Card className="flex flex-col gap-4 px-4 py-4 md:px-5.5 md:py-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.75">
          <IconTile tone={lifestyle ? "accent" : "success"} size="lg">
            <Icon size={18} aria-hidden="true" />
          </IconTile>
          <div className="flex min-w-0 flex-col gap-0.5">
            <h2 className="m-0 truncate text-[15px] font-bold">{goal.name}</h2>
            <span className="text-base text-muted-foreground">
              {metaOf(goal)} · set {SET_ON.format(new Date(goal.created_at))}
            </span>
          </div>
        </div>
        <IconButton
          aria-label={`Edit ${goal.name}`}
          className="h-11 w-11 shrink-0 md:h-auto md:w-auto"
          onClick={onEdit}
        >
          <Pencil size={16} />
        </IconButton>
      </div>

      {lifestyle ? (
        <div className="flex flex-col gap-2.5">
          {goal.description && (
            <p className="m-0 text-md text-muted-foreground">{goal.description}</p>
          )}
          <p className="m-0 text-md text-muted-foreground">
            Not a money target, so it is read through the things you buy.{" "}
            {watched.length > 0 ? "These are the lines it watches:" : "Nothing is watched yet."}
          </p>
          <ul className="m-0 flex list-none flex-wrap items-center gap-1.75 p-0">
            {watched.map((line) => (
              <li key={line}>
                <Pill>{line}</Pill>
              </li>
            ))}
            <li>
              <button
                type="button"
                aria-label={`Adjust what ${goal.name} watches`}
                onClick={onEdit}
                className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-pill border border-dashed border-border-strong bg-background px-2.75 text-base text-muted-foreground transition-colors hover:text-foreground md:min-h-0 md:py-1"
              >
                <Plus size={12} aria-hidden="true" />
                Adjust
              </button>
            </li>
          </ul>
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          <p className="m-0 text-lg font-semibold tabular-nums">
            {target(goal, currency, categoryName(goal.category_id))}
          </p>
          {goal.description && (
            <p className="m-0 text-md text-muted-foreground">{goal.description}</p>
          )}
        </div>
      )}
      {children}
    </Card>
  );
}
