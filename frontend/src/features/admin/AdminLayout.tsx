import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router-dom";

import { Button, Card, ErrorState, LoadingState } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { NotFoundPage } from "@/features/public-landing/pages/NotFoundPage";

const TAB =
  "inline-flex min-h-11 flex-1 items-center justify-center rounded-chip px-3 text-md font-semibold whitespace-nowrap md:flex-none";

/**
 * The admin console's frame (F18.6): its tabs, and the check that this session may open
 * it. An admin signed in without a second factor is sent to set it up (F18.6.1); anyone
 * else gets the page that does not exist.
 */
export const AdminLayout = observer(function AdminLayout() {
  const { authStore, adminStore } = useStores();
  const { t } = useTranslation("admin");
  const user = authStore.user;
  const isAdmin = user?.is_admin === true;

  useEffect(() => {
    if (isAdmin) void adminStore.checkAccess();
  }, [adminStore, isAdmin]);

  if (!isAdmin) return <NotFoundPage />;

  const tabs: [string, string][] = [
    ["/admin", t("nav.dashboard")],
    ["/admin/users", t("nav.users")],
    ...(user.is_super_admin ? ([["/admin/log", t("nav.log")]] as [string, string][]) : []),
  ];

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 py-4 md:gap-6 md:py-10">
      <h1 className="m-0 text-[24px] font-bold text-foreground md:text-3xl">{t("title")}</h1>
      <nav
        aria-label={t("nav.label")}
        className="flex gap-1 rounded-control border border-border bg-muted p-1 md:self-start"
      >
        {tabs.map(([to, label]) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/admin"}
            className={({ isActive }) =>
              `${TAB} ${isActive ? "bg-background text-foreground shadow-card" : "text-muted-foreground"}`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      {adminStore.access === "unknown" ? (
        <LoadingState title={t("checking")} />
      ) : adminStore.access === "second_factor" ? (
        <SecondFactorGate enabled={user.two_factor_enabled} />
      ) : adminStore.access === "denied" ? (
        <ErrorState layout="banner" title={t("failed")} message={t("deniedBody")} />
      ) : (
        <Outlet />
      )}
    </div>
  );
});

function SecondFactorGate({ enabled }: { enabled: boolean }) {
  const { authStore } = useStores();
  const { t } = useTranslation("admin");
  return (
    <Card variant="surface" className="flex flex-col gap-3 p-4 md:p-6">
      <h2 className="m-0 text-lg font-semibold">{t("gate.title")}</h2>
      <p className="m-0 text-md leading-relaxed text-muted-foreground">
        {enabled ? t("gate.signInAgainBody") : t("gate.setUpBody")}
      </p>
      {enabled ? (
        <Button
          type="button"
          className="w-full md:w-auto md:self-start"
          onClick={() => {
            void authStore.logout();
          }}
        >
          {t("gate.signInAgain")}
        </Button>
      ) : (
        <Link
          to="/profile#security"
          className="inline-flex min-h-11 w-full items-center justify-center rounded-control bg-primary px-4 font-semibold text-primary-foreground md:w-auto md:self-start"
        >
          {t("gate.setUp")}
        </Link>
      )}
    </Card>
  );
}
