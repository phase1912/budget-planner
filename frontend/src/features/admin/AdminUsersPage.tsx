import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  Button,
  Card,
  ErrorState,
  Input,
  LoadingState,
  Pagination,
  Pill,
  SegmentedControl,
} from "@/shared/components";
import { dateFormat } from "@/i18n/format";
import { ADMIN_PAGE_SIZE, type AdminUserRow, type UserFilter } from "@/stores/AdminStore";
import { useStores } from "@/stores/StoreContext";

const DAY = dateFormat({ day: "numeric", month: "short", year: "numeric" });

/**
 * Finding an account to support (F18.6.2): by address, narrowed to unconfirmed, paying or
 * recently active accounts. Rows, not a table, so a phone reads them without scrolling.
 */
export const AdminUsersPage = observer(function AdminUsersPage() {
  const { adminStore } = useStores();
  const { t } = useTranslation("admin");
  const [query, setQuery] = useState(adminStore.query);
  const { users, listState, filter, page, pages, total } = adminStore;

  useEffect(() => {
    void adminStore.loadUsers();
  }, [adminStore]);

  return (
    <section className="flex flex-col gap-4">
      <form
        role="search"
        className="flex flex-col gap-2 md:flex-row md:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          adminStore.search(query);
        }}
      >
        <Input
          id="admin-search"
          type="search"
          label={t("users.searchLabel")}
          placeholder={t("users.searchPlaceholder")}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
          }}
          containerClassName="flex-1"
        />
        <Button type="submit" variant="secondary" className="w-full md:w-auto">
          {t("users.search")}
        </Button>
      </form>
      <SegmentedControl<UserFilter>
        label={t("users.filterLabel")}
        size="sm"
        fill
        value={filter}
        onChange={(chosen) => {
          adminStore.chooseFilter(chosen);
        }}
        options={[
          { value: "all", label: t("users.all") },
          { value: "unconfirmed", label: t("users.unconfirmed") },
          { value: "paid", label: t("users.paid") },
          { value: "active", label: t("users.active"), shortLabel: t("users.activeShort") },
        ]}
      />
      {listState.error ? (
        <ErrorState layout="banner" title={t("failed")} message={listState.error} />
      ) : listState.isLoading && users.length === 0 ? (
        <LoadingState title={t("users.loading")} />
      ) : users.length === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("users.empty")}</p>
      ) : (
        <>
          <Card variant="surface" flush>
            <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
              {users.map((user) => (
                <UserLine key={user.id} user={user} />
              ))}
            </ul>
          </Card>
          {total > ADMIN_PAGE_SIZE && (
            <Pagination
              page={page}
              pages={pages}
              size={ADMIN_PAGE_SIZE}
              total={total}
              onPageChange={(next) => {
                adminStore.goToPage(next);
              }}
            />
          )}
        </>
      )}
    </section>
  );
});

function UserLine({ user }: { user: AdminUserRow }) {
  const { t } = useTranslation("admin");
  return (
    <li>
      <Link
        to={`/admin/users/${user.id}`}
        className="flex min-h-11 flex-col gap-1 px-4 py-3 text-foreground no-underline hover:bg-muted md:flex-row md:items-center md:justify-between md:gap-4"
      >
        <span className="flex min-w-0 flex-col">
          <span className="break-all font-semibold">{user.email}</span>
          <span className="text-base text-muted-foreground">
            {user.first_name} {user.last_name} ·{" "}
            {t("users.joined", { date: DAY.format(new Date(user.created_at)) })}
          </span>
        </span>
        <span className="flex flex-wrap items-center gap-2 text-base text-muted-foreground md:justify-end">
          {user.is_admin && (
            <Pill tone="accent" size="sm">
              {t("users.admin")}
            </Pill>
          )}
          {user.plan === "paid" && (
            <Pill tone="success" size="sm">
              {t("users.paidPill")}
            </Pill>
          )}
          {!user.email_confirmed && (
            <Pill tone="warning" size="sm">
              {t("users.notConfirmed")}
            </Pill>
          )}
          <span className="whitespace-nowrap">
            {user.last_active_at
              ? t("users.lastActive", { date: DAY.format(new Date(user.last_active_at)) })
              : t("users.neverActive")}
          </span>
        </span>
      </Link>
    </li>
  );
}
