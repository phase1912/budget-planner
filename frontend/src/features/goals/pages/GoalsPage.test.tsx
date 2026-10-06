import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { observable, runInAction } from "mobx";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AdviceOutcome,
  AdviceReadiness,
  GoalProgress,
  Recommendation,
} from "@/stores/AdviceStore";
import type { Goal, GoalCreate, GoalUpdate } from "@/stores/GoalsStore";
import { GoalsPage } from "./GoalsPage";

const ceiling: Goal = {
  id: "g1",
  type: "financial",
  financial_kind: "spending_ceiling",
  name: "Monthly ceiling",
  description: null,
  target_amount: "3000.00",
  category_id: null,
  mapped_category_ids: [],
  mapped_item_names: [],
  created_at: "2026-09-28T10:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
};
const eatBetter: Goal = {
  ...ceiling,
  id: "g2",
  type: "lifestyle",
  financial_kind: null,
  name: "Eat better",
  target_amount: null,
  description: "Fewer snacks",
  mapped_category_ids: ["c1"],
  mapped_item_names: ["sweets"],
};
const groceries = {
  id: "c1",
  name: "Groceries",
  is_builtin: true,
  item_count: 0,
  total_amount: "0",
};

// Observable, as the real store is, so the dialog shows a refusal once it lands.
const goalsStore = observable(
  {
    goals: [] as Goal[],
    isLoading: false,
    loadError: null as string | null,
    isSaving: false,
    saveError: null as string | null,
    load: vi.fn(),
    create: vi.fn<(goal: GoalCreate) => Promise<boolean>>(),
    update: vi.fn<(id: string, changes: GoalUpdate) => Promise<boolean>>(),
    remove: vi.fn<(id: string) => Promise<boolean>>(),
    clearSaveError: vi.fn(),
  },
  { load: false, create: false, update: false, remove: false, clearSaveError: false },
);
const adviceStore = observable(
  {
    recommendations: [] as Recommendation[],
    isLoading: false,
    loadError: null as string | null,
    advisingGoalId: null as string | null,
    outcomes: new Map<string, AdviceOutcome>(),
    readiness: null as AdviceReadiness | null,
    progress: new Map<string, GoalProgress>(),
    forGoal(goalId: string): Recommendation[] {
      return this.recommendations.filter((r) => r.goal_id === goalId);
    },
    get warnings(): GoalProgress[] {
      return [...this.progress.values()].filter((p) => p.at_risk && !p.warning_dismissed);
    },
    load: vi.fn(),
    loadProgress: vi.fn(),
    dismissWarning: vi.fn<(goalId: string) => Promise<void>>(),
    advise: vi.fn<(goalId: string) => Promise<void>>(),
  },
  { load: false, loadProgress: false, dismissWarning: false, advise: false },
);
const cookies: Recommendation = {
  id: "r1",
  goal_id: "g2",
  target_kind: "item",
  target_name: "Cookies Choco 300g",
  action: "Stop buying the chocolate-chip cookies",
  rationale: "On 9 of the 14 receipts from Fresh Market.",
  reduction_percent: 100,
  monthly_saving: "20.47",
  purchases_avoided: "3.0",
  created_at: "2026-09-30T10:00:00Z",
};
const categoriesStore = {
  categories: [groceries],
  assignableBuiltIns: [groceries],
  customCategories: [],
  ensureCategories: vi.fn(),
};

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    goalsStore,
    adviceStore,
    categoriesStore,
    authStore: { user: { currency: "PLN" } },
  }),
}));

function openNewGoal() {
  render(<GoalsPage />);
  fireEvent.click(screen.getByRole("button", { name: /new goal/i }));
  return screen.getByRole("dialog");
}

describe("GoalsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runInAction(() => {
      goalsStore.goals = [];
      goalsStore.loadError = null;
      goalsStore.saveError = null;
      adviceStore.recommendations = [];
      adviceStore.advisingGoalId = null;
      adviceStore.outcomes.clear();
      adviceStore.readiness = null;
      adviceStore.progress.clear();
      adviceStore.loadError = null;
    });
    goalsStore.create.mockResolvedValue(true);
    goalsStore.update.mockResolvedValue(true);
    goalsStore.remove.mockResolvedValue(true);
  });

  it("loads the goals and offers a first one when there are none", () => {
    render(<GoalsPage />);
    expect(goalsStore.load).toHaveBeenCalled();
    expect(screen.getByText("No goals yet")).toBeInTheDocument();
  });

  it("shows money and lifestyle goals as the user stated them", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling, eatBetter];
    });
    render(<GoalsPage />);
    expect(screen.getByText("Stay under 3,000.00 PLN a month")).toBeInTheDocument();
    expect(screen.getByText("Fewer snacks")).toBeInTheDocument();
    expect(screen.getByText(/Lifestyle goal · set/)).toBeInTheDocument();
  });

  it("says why the goals could not be loaded", () => {
    runInAction(() => {
      goalsStore.loadError = "Token expired.";
    });
    render(<GoalsPage />);
    expect(screen.getByText("Token expired.")).toBeInTheDocument();
  });

  it("keeps the cursor in the name field while it is typed", () => {
    openNewGoal();
    const name = screen.getByLabelText("Name");
    name.focus();
    let typed = "";
    for (const ch of "Save more") {
      typed += ch;
      fireEvent.change(name, { target: { value: typed } });
      expect(document.activeElement).toBe(name);
    }
    expect(name).toHaveValue("Save more");
  });

  it("states a spending ceiling with the amount typed with a comma", async () => {
    openNewGoal();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ceiling" } });
    fireEvent.change(screen.getByLabelText("Monthly ceiling, PLN"), {
      target: { value: "2500,50" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add goal" }));
    await waitFor(() => {
      expect(goalsStore.create).toHaveBeenCalledWith({
        type: "financial",
        name: "Ceiling",
        description: null,
        financial_kind: "spending_ceiling",
        target_amount: "2500.50",
        category_id: null,
      });
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("asks for the category a reduction cuts", async () => {
    openNewGoal();
    fireEvent.change(screen.getByLabelText("What kind of goal"), {
      target: { value: "category_reduction" },
    });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Fewer groceries" } });
    fireEvent.change(screen.getByLabelText("Monthly limit for that category, PLN"), {
      target: { value: "800" },
    });
    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "c1" } });
    fireEvent.click(screen.getByRole("button", { name: "Add goal" }));
    await waitFor(() => {
      expect(goalsStore.create).toHaveBeenCalledWith(
        expect.objectContaining({ financial_kind: "category_reduction", category_id: "c1" }),
      );
    });
  });

  it("states a lifestyle goal without an amount", async () => {
    openNewGoal();
    fireEvent.change(screen.getByLabelText("What kind of goal"), {
      target: { value: "lifestyle" },
    });
    expect(screen.queryByLabelText(/PLN/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Eat better" } });
    fireEvent.click(screen.getByRole("button", { name: "Add goal" }));
    await waitFor(() => {
      expect(goalsStore.create).toHaveBeenCalledWith(
        expect.objectContaining({ type: "lifestyle", financial_kind: null, target_amount: null }),
      );
    });
  });

  it("keeps the dialog open with the server's reason when a goal is refused", async () => {
    goalsStore.create.mockImplementation(() => {
      runInAction(() => {
        goalsStore.saveError = "A money goal needs an amount above zero.";
      });
      return Promise.resolve(false);
    });
    render(<GoalsPage />);
    fireEvent.click(screen.getByRole("button", { name: /new goal/i }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Zero" } });
    fireEvent.change(screen.getByLabelText("Monthly ceiling, PLN"), { target: { value: "0" } });
    fireEvent.click(screen.getByRole("button", { name: "Add goal" }));
    await waitFor(() => {
      expect(goalsStore.create).toHaveBeenCalled();
    });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("A money goal needs an amount above zero.")).toBeInTheDocument();
  });

  it("does not let a lifestyle goal be turned into a money goal", () => {
    runInAction(() => {
      goalsStore.goals = [eatBetter];
    });
    render(<GoalsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Edit Eat better" }));
    expect(screen.getByLabelText("What kind of goal")).toBeDisabled();
  });

  it("asks once more before removing a goal", async () => {
    runInAction(() => {
      goalsStore.goals = [ceiling];
    });
    render(<GoalsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Edit Monthly ceiling" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove goal" }));
    expect(goalsStore.remove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Yes, remove this goal" }));
    await waitFor(() => {
      expect(goalsStore.remove).toHaveBeenCalledWith("g1");
    });
  });

  it("shows what a lifestyle goal watches, and adjusting it opens the goal", () => {
    runInAction(() => {
      goalsStore.goals = [eatBetter];
    });
    render(<GoalsPage />);
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("sweets")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Adjust what Eat better watches" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("sends the user's correction of what a lifestyle goal watches", async () => {
    runInAction(() => {
      goalsStore.goals = [eatBetter];
    });
    render(<GoalsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Edit Eat better" }));
    fireEvent.click(screen.getByRole("button", { name: "Groceries", pressed: true }));
    fireEvent.click(screen.getByRole("button", { name: "Stop watching sweets" }));
    const add = screen.getByLabelText("Add an item");
    fireEvent.change(add, { target: { value: " Beer " } });
    fireEvent.keyDown(add, { key: "Enter" });
    expect(goalsStore.update).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => {
      expect(goalsStore.update).toHaveBeenCalledWith(
        "g2",
        expect.objectContaining({ mapped_category_ids: [], mapped_item_names: ["beer"] }),
      );
    });
  });

  it("leaves what a goal watches to the server when the user did not correct it", async () => {
    runInAction(() => {
      goalsStore.goals = [eatBetter];
    });
    render(<GoalsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Edit Eat better" }));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => {
      expect(goalsStore.update).toHaveBeenCalled();
    });
    expect(goalsStore.update.mock.lastCall?.[1]).not.toHaveProperty("mapped_item_names");
  });

  it("shows each goal's advice in its own card, the reason on demand", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling, eatBetter];
      adviceStore.recommendations = [cookies];
    });
    render(<GoalsPage />);
    expect(adviceStore.load).toHaveBeenCalled();
    const eating = within(screen.getByRole("region", { name: "Advice on Eat better" }));
    const ceilingAdvice = within(screen.getByRole("region", { name: "Advice on Monthly ceiling" }));
    expect(eating.getByText("Stop buying the chocolate-chip cookies")).toBeInTheDocument();
    expect(eating.getByText("−20.47 PLN a month · 3 fewer purchases")).toBeVisible();
    expect(eating.getByText("On 9 of the 14 receipts from Fresh Market.")).not.toBeVisible();
    fireEvent.click(eating.getByText("Why?"));
    expect(eating.getByText("On 9 of the 14 receipts from Fresh Market.")).toBeVisible();
    expect(ceilingAdvice.queryByText("Stop buying the chocolate-chip cookies")).toBeNull();
  });

  it("asks for advice on one goal from its card, and offers a refresh once it has some", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling, eatBetter];
      adviceStore.recommendations = [cookies];
    });
    render(<GoalsPage />);
    fireEvent.click(screen.getByRole("button", { name: "Get advice on Monthly ceiling" }));
    expect(adviceStore.advise).toHaveBeenCalledWith("g1");
    expect(
      screen.getByRole("button", { name: "Refresh advice on Eat better" }),
    ).toBeInTheDocument();
  });

  it("holds every advice button while one goal's advice is worked out", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling, eatBetter];
      adviceStore.advisingGoalId = "g2";
    });
    render(<GoalsPage />);
    expect(screen.getByRole("button", { name: "Get advice on Monthly ceiling" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Get advice on Eat better" })).toHaveTextContent(
      "Working it out…",
    );
    const eating = within(screen.getByRole("region", { name: "Advice on Eat better" }));
    expect(eating.getByText("Reading your receipts…")).toBeInTheDocument();
  });

  it("says in the goal's own card why it got no advice", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling, eatBetter];
      adviceStore.outcomes.set("g2", {
        kind: "failed",
        message: "Advice could not be worked out just now.",
      });
    });
    render(<GoalsPage />);
    const eating = within(screen.getByRole("region", { name: "Advice on Eat better" }));
    const ceilingAdvice = within(screen.getByRole("region", { name: "Advice on Monthly ceiling" }));
    expect(eating.getByText("Advice could not be worked out just now.")).toBeInTheDocument();
    expect(ceilingAdvice.queryByText("Advice could not be worked out just now.")).toBeNull();
  });

  it("says how far there is to go instead of offering advice on too little history", () => {
    runInAction(() => {
      goalsStore.goals = [eatBetter];
      adviceStore.readiness = {
        ready: false,
        receipts: 3,
        required_receipts: 4,
        history_days: 12,
        required_days: 30,
        progress: 40,
      };
    });
    render(<GoalsPage />);
    const eating = within(screen.getByRole("region", { name: "Advice on Eat better" }));
    expect(eating.getByText("3 receipts is not a pattern yet")).toBeInTheDocument();
    expect(eating.getByText("3 of 4 receipts · 12 of 30 days")).toBeInTheDocument();
    expect(eating.queryByRole("button", { name: /advice/ })).toBeNull();
  });

  it("says there is nothing to cut for a goal on track, and offers no advice for it", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling];
      adviceStore.recommendations = [{ ...cookies, goal_id: "g1" }];
      adviceStore.progress.set("g1", {
        goal_id: "g1",
        goal_name: "Monthly ceiling",
        at_risk: false,
        warning_dismissed: false,
        spent: "1800.00",
        projected: "2066.67",
        target: "3000.00",
        margin: "933.33",
        on_track: true,
        day: 27,
        days_in_month: 31,
      });
    });
    render(<GoalsPage />);
    const card = within(screen.getByRole("region", { name: "Advice on Monthly ceiling" }));
    expect(card.getByText("Nothing to cut this month")).toBeInTheDocument();
    expect(card.getByText("2,066.67 PLN")).toBeInTheDocument();
    expect(card.getByText(/1,200.00 PLN left/)).toBeInTheDocument();
    expect(card.getByText(/a forecast, not a promise/)).toBeInTheDocument();
    expect(card.queryByText("Stop buying the chocolate-chip cookies")).toBeNull();
    expect(card.queryByRole("button", { name: /advice/ })).toBeNull();
    expect(card.queryByText(/rough guess/)).toBeNull();
  });

  it("warns about a goal heading over its limit, and sets the warning aside on request", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling];
      adviceStore.progress.set("g1", {
        goal_id: "g1",
        goal_name: "Monthly ceiling",
        spent: "2400.00",
        projected: "3100.00",
        target: "3000.00",
        margin: "-100.00",
        on_track: false,
        at_risk: true,
        warning_dismissed: false,
        day: 24,
        days_in_month: 31,
      });
    });
    render(<GoalsPage />);
    const warnings = within(screen.getByRole("list", { name: "Goals at risk" }));
    expect(warnings.getByText("Monthly ceiling is heading over its limit")).toBeInTheDocument();
    expect(warnings.getByText(/100.00 PLN over your limit/)).toBeInTheDocument();
    fireEvent.click(
      warnings.getByRole("button", {
        name: "Set aside the warning for Monthly ceiling until next month",
      }),
    );
    expect(adviceStore.dismissWarning).toHaveBeenCalledWith("g1");
  });

  it("does not warn about a goal whose warning was set aside", () => {
    runInAction(() => {
      goalsStore.goals = [ceiling];
      adviceStore.progress.set("g1", {
        goal_id: "g1",
        goal_name: "Monthly ceiling",
        spent: "2400.00",
        projected: "3100.00",
        target: "3000.00",
        margin: "-100.00",
        on_track: false,
        at_risk: true,
        warning_dismissed: true,
        day: 24,
        days_in_month: 31,
      });
    });
    render(<GoalsPage />);
    expect(screen.queryByRole("list", { name: "Goals at risk" })).toBeNull();
  });
});
