import { observer } from "mobx-react-lite";
import { ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { dateFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";
import { MonthStatus } from "./MonthStatus";

const MONTH = dateFormat({ month: "long" });
const MONTH_AND_YEAR = dateFormat({ month: "long", year: "numeric" });

/**
 * Home's top (design v2): a greeting, the month between its arrows — never past the
 * current one (D2) — whether it is still running (D4), the assistant to ask about it
 * (F21.1) and the avatar that opens Settings. Wider screens reach both from the side menu.
 */
export const HomeHeader = observer(function HomeHeader({ isComplete }: { isComplete: boolean }) {
  const { authStore, budgetStore } = useStores();
  const { t } = useTranslation("dashboard");
  const { t: common } = useTranslation("common");
  const user = authStore.user;
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? t("welcome.morning") : hour < 18 ? t("welcome.afternoon") : t("welcome.evening");
  const shown = new Date(budgetStore.year, budgetStore.month - 1, 1);
  const label =
    budgetStore.year === budgetStore.current.year
      ? MONTH.format(shown)
      : MONTH_AND_YEAR.format(shown);
  const initials =
    `${user?.first_name.charAt(0) ?? ""}${user?.last_name.charAt(0) ?? ""}`.toUpperCase() || "?";
  const arrow =
    "flex h-11 w-9 items-center justify-center rounded-chip text-foreground disabled:opacity-30";

  return (
    <header className="flex items-center justify-between gap-3">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-md text-muted-foreground">
          {t("welcome.greeting", { greeting, name: user?.first_name ?? "" })}
        </span>
        <nav aria-label={t("switcher.month")} className="-ml-2.5 flex items-center">
          <button
            type="button"
            aria-label={t("switcher.previous")}
            className={arrow}
            onClick={() => void budgetStore.showPreviousMonth()}
          >
            <ChevronLeft size={22} strokeWidth={2.4} aria-hidden="true" />
          </button>
          <h1
            aria-live="polite"
            className="m-0 truncate text-2xl font-extrabold tracking-[-0.02em] first-letter:uppercase md:text-3xl"
          >
            {label}
          </h1>
          <button
            type="button"
            aria-label={t("switcher.next")}
            className={arrow}
            disabled={!budgetStore.canGoForward}
            onClick={() => void budgetStore.showNextMonth()}
          >
            <ChevronRight size={22} strokeWidth={2.4} aria-hidden="true" />
          </button>
          <span className="ml-1 hidden md:inline-flex">
            <MonthStatus isComplete={isComplete} compact />
          </span>
        </nav>
      </div>
      {/* The assistant sits by the avatar, as it sits by the brand in the side menu. */}
      <div className="flex shrink-0 items-center gap-2 md:hidden">
        <Link
          to="/assistant"
          aria-label={common("nav.assistant")}
          className="flex h-11 w-11 items-center justify-center rounded-pill bg-tone-primary-bg text-primary"
        >
          <Sparkles size={20} aria-hidden="true" />
        </Link>
        <Link
          to="/settings"
          aria-label={t("hero.settings")}
          className="flex h-11 w-11 items-center justify-center rounded-pill bg-tone-primary-bg text-md font-extrabold text-primary"
        >
          {initials}
        </Link>
      </div>
    </header>
  );
});
