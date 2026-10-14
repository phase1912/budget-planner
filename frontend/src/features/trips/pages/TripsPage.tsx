import { useEffect, useState } from "react";
import { Plane, Plus } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { SectionTabs } from "@/features/app-shell/SectionTabs";
import { formatAmount } from "@/i18n/format";
import { Button, EmptyState, ErrorState, LoadingState, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { TripRequest } from "@/stores/TripsStore";
import { TripCard } from "../components/TripCard";
import { TripDialog } from "../components/TripDialog";
import { formatTripDay } from "../tripFormat";

/**
 * The user's trips (F20.1): stretches of receipts in a foreign currency offered as
 * trips nobody recorded yet, then every trip, newest first, each opening to its page.
 */
export const TripsPage = observer(function TripsPage() {
  const { tripsStore, authStore } = useStores();
  const { t } = useTranslation("trips");
  const navigate = useNavigate();
  const [draft, setDraft] = useState<Partial<TripRequest> | null>(null);
  const currency = authStore.user?.currency ?? "PLN";
  const { trips, isLoading, loadError } = tripsStore;

  useEffect(() => {
    void tripsStore.load();
  }, [tripsStore]);

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5">
        <SectionTabs />
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[24px] font-bold tracking-[-0.02em] md:text-[28px]">
              {t("title")}
            </h1>
            <p className="m-0 text-lg text-muted-foreground">{t("subtitle")}</p>
          </div>
          <Button
            className="w-full md:w-auto"
            onClick={() => {
              setDraft({});
            }}
          >
            <Plus size={16} aria-hidden="true" />
            {t("new")}
          </Button>
        </header>

        {tripsStore.openSuggestions.map((suggestion) => (
          <Note key={`${suggestion.start}:${suggestion.currency}`} tone="info">
            <div className="flex flex-col gap-2.5 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-col gap-0.5">
                <strong>{t("suggestions.title")}</strong>
                <span>
                  {t("suggestions.text", {
                    start: formatTripDay(suggestion.start),
                    end: formatTripDay(suggestion.end),
                    count: suggestion.receipts,
                    currency: suggestion.currency,
                    amount: `${formatAmount(suggestion.amount)} ${suggestion.currency}`,
                  })}
                </span>
              </div>
              <div className="flex gap-2 [&>*]:flex-1 md:[&>*]:flex-none">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    tripsStore.dismissSuggestion(suggestion);
                  }}
                >
                  {t("suggestions.dismiss")}
                </Button>
                <Button
                  size="sm"
                  onClick={() => {
                    setDraft({ start_date: suggestion.start, end_date: suggestion.end });
                  }}
                >
                  {t("suggestions.record")}
                </Button>
              </div>
            </div>
          </Note>
        ))}

        {loadError ? (
          <ErrorState title={t("title")} message={loadError} layout="banner" />
        ) : isLoading && trips.length === 0 ? (
          <LoadingState layout="skeleton" />
        ) : trips.length === 0 ? (
          <EmptyState icon={Plane} title={t("title")} message={t("empty")} />
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {trips.map((trip) => (
              <li key={trip.id}>
                <TripCard trip={trip} currency={currency} />
              </li>
            ))}
          </ul>
        )}
      </div>
      {draft && (
        <TripDialog
          initial={draft}
          onClose={() => {
            setDraft(null);
          }}
          onSaved={(id) => {
            void navigate(`/trips/${id}`);
          }}
        />
      )}
    </div>
  );
});
