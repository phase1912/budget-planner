import { useEffect, useState, type ReactNode } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";

import {
  Button,
  Card,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  ModalBody,
  Note,
  Pill,
  Select,
} from "@/shared/components";
import { dateFormat } from "@/i18n/format";
import type { AdminUserCard } from "@/stores/AdminStore";
import { useStores } from "@/stores/StoreContext";

const DAY = dateFormat({ day: "numeric", month: "short", year: "numeric" });
const MOMENT = dateFormat({ day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const GRANT_DAYS = [7, 30, 90, 365] as const;

const day = (iso: string) => DAY.format(new Date(iso.length === 10 ? `${iso}T00:00:00` : iso));

/**
 * One account, for supporting it (F18.6.2, F18.6.3): who it is, how it is set up and
 * used, its plan and grants, and the actions an admin may take. Never its receipts (N2).
 */
export const AdminUserPage = observer(function AdminUserPage() {
  const { adminStore } = useStores();
  const { t } = useTranslation("admin");
  const { id = "" } = useParams();
  const { card, cardState } = adminStore;

  useEffect(() => {
    void adminStore.loadCard(id);
  }, [adminStore, id]);

  return (
    <section className="flex flex-col gap-4 md:gap-6">
      <Link
        to="/admin/users"
        className="inline-flex min-h-11 items-center gap-1 self-start text-md font-semibold text-primary"
      >
        <ChevronLeft size={16} aria-hidden="true" />
        {t("user.back")}
      </Link>
      {cardState.error && !card ? (
        <ErrorState layout="banner" title={t("failed")} message={cardState.error} />
      ) : card?.id !== id ? (
        <LoadingState title={t("user.loading")} />
      ) : (
        <Account card={card} />
      )}
    </section>
  );
});

const Account = observer(function Account({ card }: { card: AdminUserCard }) {
  const { adminStore } = useStores();
  const { t } = useTranslation("admin");
  const role = card.is_super_admin
    ? t("user.roleSuper")
    : card.is_admin
      ? t("user.roleAdmin")
      : t("user.roleUser");

  return (
    <>
      <header className="flex flex-col gap-2">
        <h2 className="m-0 break-all text-xl font-bold">{card.email}</h2>
        <p className="m-0 text-md text-muted-foreground">{t("user.privacy")}</p>
      </header>
      {adminStore.actionState.error && <Note tone="error">{adminStore.actionState.error}</Note>}

      <Section title={t("user.facts")}>
        <dl className="m-0 grid grid-cols-1 gap-x-6 gap-y-3 md:grid-cols-2">
          <Fact label={t("user.name")}>
            {card.first_name} {card.last_name}
          </Fact>
          <Fact label={t("user.joined")}>{day(card.created_at)}</Fact>
          <Fact label={t("user.confirmed")}>
            {card.email_confirmed_at ? day(card.email_confirmed_at) : t("user.notConfirmed")}
          </Fact>
          <Fact label={t("user.lastActive")}>
            {card.last_active_at ? day(card.last_active_at) : t("user.never")}
          </Fact>
          <Fact label={t("user.language")}>
            {card.language?.toUpperCase() ?? t("user.languageNone")}
          </Fact>
          <Fact label={t("user.terms")}>{card.terms_version ?? "—"}</Fact>
          <Fact label={t("user.twoFactor")}>
            {card.two_factor_enabled ? t("user.on") : t("user.off")}
          </Fact>
          <Fact label={t("user.role")}>{role}</Fact>
        </dl>
      </Section>

      <Support card={card} />
      <PlanSection card={card} />
      <RoleSection card={card} />

      <Section title={t("user.activity")}>
        {card.activity.length === 0 ? (
          <p className="m-0 text-md text-muted-foreground">{t("user.noActivity")}</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {card.activity.map((event, index) => (
              <li
                key={`${event.created_at}-${String(index)}`}
                className="flex flex-wrap justify-between gap-x-3 text-md"
              >
                <span>{t(`events.${event.event}` as "events.active", event.event)}</span>
                <span className="tabular-nums text-muted-foreground">
                  {MOMENT.format(new Date(event.created_at))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </>
  );
});

const Support = observer(function Support({ card }: { card: AdminUserCard }) {
  const { adminStore, authStore } = useStores();
  const { t } = useTranslation("admin");
  const busy = adminStore.actionState.isLoading;
  return (
    <Section title={t("user.support")}>
      <div className="flex flex-col gap-2 md:flex-row md:flex-wrap">
        {!card.email_confirmed_at && (
          <>
            <Button
              type="button"
              className="w-full md:w-auto"
              disabled={busy}
              onClick={() => void adminStore.confirmEmail(card.id)}
            >
              {t("user.confirmEmail")}
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="w-full md:w-auto"
              disabled={busy}
              onClick={() => void adminStore.sendConfirmation(card.id)}
            >
              {t("user.sendConfirmation")}
            </Button>
          </>
        )}
        <Button
          type="button"
          variant="secondary"
          className="w-full md:w-auto"
          disabled={busy}
          onClick={() => void adminStore.sendPasswordReset(card.id)}
        >
          {t("user.sendReset")}
        </Button>
        <Button
          type="button"
          variant="secondary"
          className="w-full md:w-auto"
          disabled={busy || card.onboarded_at === null}
          onClick={() => {
            void adminStore.restartOnboarding(card.id).then((ok) => {
              // One's own account goes to the setup straight away, to test it.
              const me = authStore.user;
              if (ok && me?.id === card.id) authStore.updateUser({ ...me, onboarded_at: null });
            });
          }}
        >
          {t("user.restartOnboarding")}
        </Button>
      </div>
      <p className="m-0 text-base text-muted-foreground">{t("user.resetNote")}</p>
      <p className="m-0 text-base text-muted-foreground">
        {card.onboarded_at === null ? t("user.onboardingPending") : t("user.onboardingNote")}
      </p>
    </Section>
  );
});

const PlanSection = observer(function PlanSection({ card }: { card: AdminUserCard }) {
  const { adminStore } = useStores();
  const { t } = useTranslation("admin");
  const [days, setDays] = useState<number>(30);
  const [reason, setReason] = useState("");
  const [revoking, setRevoking] = useState<string | null>(null);
  const busy = adminStore.actionState.isLoading;

  return (
    <Section title={t("user.plan")}>
      <p className="m-0 flex flex-wrap items-center gap-2 text-md">
        <Pill tone={card.plan === "paid" ? "success" : "default"} size="sm">
          {card.plan === "paid" ? t("user.planPaid") : t("user.planFree")}
        </Pill>
        {card.plan_ends_on && t("user.planUntil", { date: day(card.plan_ends_on) })}
      </p>
      <p className="m-0 text-md">
        <span className="text-muted-foreground">{t("user.reads")}: </span>
        <span className="tabular-nums">
          {card.receipts_limit === null
            ? t("user.readsUnlimited", { used: card.receipts_used })
            : t("user.readsOf", { used: card.receipts_used, limit: card.receipts_limit })}
        </span>
      </p>

      <form
        className="flex flex-col gap-3 rounded-control border border-border p-3 md:p-4"
        onSubmit={(event) => {
          event.preventDefault();
          void adminStore.grantPlan(card.id, days, reason).then((done) => {
            if (done) setReason("");
          });
        }}
      >
        <h4 className="m-0 text-md font-semibold">{t("user.grantTitle")}</h4>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[auto_1fr]">
          <Select
            id="grant-days"
            label={t("user.grantDays")}
            value={days}
            onChange={(event) => {
              setDays(Number(event.target.value));
            }}
          >
            {GRANT_DAYS.map((n) => (
              <option key={n} value={n}>
                {t("days.d", { count: n })}
              </option>
            ))}
          </Select>
          <Input
            id="grant-reason"
            label={t("user.grantReason")}
            placeholder={t("user.grantReasonPlaceholder")}
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
            }}
            minLength={3}
            maxLength={200}
            required
          />
        </div>
        <p className="m-0 text-base text-muted-foreground">{t("user.grantNote")}</p>
        <Button
          type="submit"
          className="w-full md:w-auto md:self-start"
          disabled={busy || reason.trim().length < 3}
        >
          {t("user.grant")}
        </Button>
      </form>

      <h4 className="m-0 text-md font-semibold">{t("user.grants")}</h4>
      {card.grants.length === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("user.noGrants")}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
          {card.grants.map((grant) => (
            <li
              key={grant.id}
              className="flex flex-col gap-2 py-2.5 md:flex-row md:items-center md:justify-between"
            >
              <span className="flex flex-col gap-0.5">
                <span className="tabular-nums font-medium">
                  {t("user.grantLine", { start: day(grant.starts_at), end: day(grant.ends_at) })}
                </span>
                <span className="break-words text-base text-muted-foreground">
                  {grant.reason}
                  {grant.granted_by && ` · ${t("user.grantedBy", { who: grant.granted_by })}`}
                </span>
              </span>
              {grant.revoked_at ? (
                <Pill size="sm" className="self-start md:self-center">
                  {t("user.revoked")}
                </Pill>
              ) : (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="w-full md:w-auto"
                  disabled={busy}
                  onClick={() => {
                    setRevoking(grant.id);
                  }}
                >
                  {t("user.revoke")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {revoking && (
        <ConfirmDialog
          body={t("user.confirmRevoke")}
          onCancel={() => {
            setRevoking(null);
          }}
          onConfirm={() => {
            const grantId = revoking;
            setRevoking(null);
            void adminStore.revokeGrant(card.id, grantId);
          }}
        />
      )}
    </Section>
  );
});

const RoleSection = observer(function RoleSection({ card }: { card: AdminUserCard }) {
  const { adminStore, authStore } = useStores();
  const { t } = useTranslation("admin");
  const [asking, setAsking] = useState(false);
  if (authStore.user?.is_super_admin !== true) return null;
  const appoint = !card.is_admin;

  return (
    <Section title={t("user.roleTitle")}>
      {card.is_super_admin ? (
        <p className="m-0 text-md text-muted-foreground">{t("user.superFixed")}</p>
      ) : (
        <Button
          type="button"
          variant={appoint ? "secondary" : "danger"}
          className="w-full md:w-auto md:self-start"
          disabled={adminStore.actionState.isLoading}
          onClick={() => {
            setAsking(true);
          }}
        >
          {appoint ? t("user.appoint") : t("user.remove")}
        </Button>
      )}
      {asking && (
        <ConfirmDialog
          body={appoint ? t("user.confirmAppoint") : t("user.confirmRemove")}
          onCancel={() => {
            setAsking(false);
          }}
          onConfirm={() => {
            setAsking(false);
            void adminStore.setAdmin(card.id, appoint);
          }}
        />
      )}
    </Section>
  );
});

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card variant="surface" className="flex flex-col gap-3 p-4 md:p-5">
      <h3 className="m-0 text-lg font-semibold">{title}</h3>
      {children}
    </Card>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-base text-muted-foreground">{label}</dt>
      <dd className="m-0 break-words text-md">{children}</dd>
    </div>
  );
}

function ConfirmDialog({
  body,
  onCancel,
  onConfirm,
}: {
  body: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const { t } = useTranslation("admin");
  return (
    <Modal
      isOpen
      onClose={onCancel}
      className="w-full md:max-w-[420px]"
      aria-labelledby="admin-confirm"
    >
      <ModalBody className="flex flex-col gap-4">
        <h2 id="admin-confirm" className="m-0 text-lg font-bold">
          {t("user.confirmTitle")}
        </h2>
        <p className="m-0 text-md leading-relaxed text-muted-foreground">{body}</p>
        <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
          <Button type="button" variant="secondary" className="w-full md:w-auto" onClick={onCancel}>
            {t("user.cancel")}
          </Button>
          <Button type="button" className="w-full md:w-auto" onClick={onConfirm}>
            {t("user.yes")}
          </Button>
        </div>
      </ModalBody>
    </Modal>
  );
}
