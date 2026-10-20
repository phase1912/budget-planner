import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRightLeft, ChevronRight, Plus, Wallet } from "lucide-react";

import { BackLink, Button, ErrorState, LoadingState, SegmentedControl } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { KIND_ICON, WHOLE, kindLineKey, rateText } from "../accountFormat";
import { AccountDialog } from "../components/AccountDialog";
import { MoveDialog } from "../components/MoveDialog";
import { ToCheck } from "../components/ToCheck";

type Filter = "all" | "shared" | "mine";

/**
 * Where the money is (F23.15, canvas F_Accounts): every account the user sees — their own
 * and the family's shared ones — what is on them together and what of it is the tax
 * office's, what is waiting to be checked, and moving money between them.
 */
export const AccountsPage = observer(function AccountsPage() {
  const { bankAccountsStore, budgetStore, householdStore, incomeStore, authStore } = useStores();
  const { t } = useTranslation("accounts");
  const [filter, setFilter] = useState<Filter>("all");
  const [adding, setAdding] = useState(false);
  const [moving, setMoving] = useState(false);
  const today = budgetStore.today;
  const currency = authStore.user?.currency ?? "PLN";

  useEffect(() => {
    void bankAccountsStore.load(today);
    void bankAccountsStore.loadExpected(today);
    void incomeStore.loadPending();
    if (!householdStore.loaded) void householdStore.load();
  }, [bankAccountsStore, incomeStore, householdStore, today]);

  const { accounts, state } = bankAccountsStore;
  const shown = accounts.filter(
    (a) => filter === "all" || (filter === "shared" ? a.shared : !a.shared),
  );
  const total = shown.reduce((sum, a) => sum + Number(a.balance), 0);
  const setAside = shown.reduce((sum, a) => sum + Number(a.set_aside), 0);
  const inFamily = householdStore.shared;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 py-4 md:gap-5 md:py-2">
      <div className="flex items-center gap-3">
        <BackLink to="/plan" label={t("back")} />
        <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em]">{t("title")}</h1>
      </div>

      {!bankAccountsStore.loaded ? (
        <LoadingState title={t("title")} />
      ) : state.error && accounts.length === 0 ? (
        <ErrorState layout="banner" title={t("title")} message={state.error} />
      ) : accounts.length === 0 ? (
        <section className="flex flex-col items-start gap-3 rounded-hero bg-surface p-5 md:p-6">
          <span className="flex h-12 w-12 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
            <Wallet size={24} aria-hidden="true" />
          </span>
          <h2 className="m-0 text-xl font-extrabold">{t("empty.title")}</h2>
          <p className="m-0 text-md leading-relaxed text-muted-foreground">{t("empty.body")}</p>
          <Button
            className="min-h-11 w-full md:w-auto"
            onClick={() => {
              setAdding(true);
            }}
          >
            <Plus size={18} aria-hidden="true" />
            {t("add")}
          </Button>
        </section>
      ) : (
        <>
          <section
            aria-label={t(`total.${filter}`)}
            className="flex flex-col gap-1 rounded-hero bg-surface p-5 md:p-6"
          >
            <span className="text-md font-semibold text-muted-foreground">
              {t(`total.${filter}`)}
            </span>
            <span className="text-4xl font-extrabold tabular-nums">
              {WHOLE.format(total)} {currency}
            </span>
            {setAside > 0 && (
              <span className="text-md font-semibold text-tone-warning-text tabular-nums">
                {t("setAside", { amount: WHOLE.format(setAside), currency })}
              </span>
            )}
          </section>

          {inFamily && (
            <div className="on-surface">
              <SegmentedControl<Filter>
                label={t("filters.label")}
                fill
                value={filter}
                onChange={setFilter}
                options={[
                  { value: "all", label: t("filters.all") },
                  { value: "shared", label: t("filters.shared") },
                  { value: "mine", label: t("filters.mine") },
                ]}
              />
            </div>
          )}

          <ToCheck today={today} />

          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {shown.map((account) => {
              const Icon = KIND_ICON[account.kind];
              return (
                <li key={account.id}>
                  <Link
                    to={`/accounts/${account.id}`}
                    className="flex min-h-16 items-center gap-3.5 rounded-card bg-surface px-4 py-3 text-foreground no-underline"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
                      <Icon size={20} aria-hidden="true" />
                    </span>
                    <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="truncate text-lg font-bold">{account.name}</span>
                      <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5">
                        {inFamily && (
                          <span
                            className={`shrink-0 rounded-pill px-2 py-0.5 text-xs font-extrabold ${
                              account.shared
                                ? "bg-tone-primary-bg text-primary"
                                : "bg-muted text-foreground"
                            }`}
                          >
                            {account.shared ? t("shared") : t("mine")}
                          </span>
                        )}
                        <span className="min-w-0 text-md text-muted-foreground">
                          {[
                            t(kindLineKey(account), { rate: rateText(account.tax_rate) }),
                            account.for_purchases ? t("purchases") : null,
                            account.added_by ? t("addedBy", { name: account.added_by }) : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </span>
                      </span>
                    </span>
                    {/* A card in the red is shown so: most likely a top-up not entered. */}
                    <span
                      className={`shrink-0 text-lg font-extrabold tabular-nums ${
                        Number(account.balance) < 0 ? "text-error" : ""
                      }`}
                    >
                      {WHOLE.format(Number(account.balance))} {currency}
                    </span>
                    <ChevronRight
                      size={18}
                      aria-hidden="true"
                      className="shrink-0 text-muted-foreground"
                    />
                  </Link>
                </li>
              );
            })}
          </ul>

          {inFamily && <p className="m-0 text-md text-muted-foreground">{t("othersOwn")}</p>}

          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {accounts.length > 1 && (
              <Button
                variant="secondary"
                className="min-h-11"
                onClick={() => {
                  setMoving(true);
                }}
              >
                <ArrowRightLeft size={18} aria-hidden="true" />
                {t("move")}
              </Button>
            )}
            <Button
              variant="secondary"
              className="min-h-11"
              onClick={() => {
                setAdding(true);
              }}
            >
              <Plus size={18} aria-hidden="true" />
              {t("add")}
            </Button>
          </div>
        </>
      )}

      {adding && (
        <AccountDialog
          account={null}
          today={today}
          onClose={() => {
            setAdding(false);
          }}
        />
      )}
      {moving && (
        <MoveDialog
          today={today}
          onClose={() => {
            setMoving(false);
          }}
        />
      )}
    </div>
  );
});
