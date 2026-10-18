import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button, Card, Note } from "@/shared/components";
import type { HouseholdInvite } from "@/stores/HouseholdStore";
import { useStores } from "@/stores/StoreContext";
import { Trans, useTranslation } from "react-i18next";

/**
 * Where an invite link lands (E12 — F12.3, ADR-0017): whose household it is, what joining
 * shares, and a Join button. A visitor who is not signed in is sent to sign in or register
 * first and brought back here by ProtectedRoute.
 */
export const JoinHouseholdPage = observer(function JoinHouseholdPage() {
  const { householdStore } = useStores();
  const { t } = useTranslation("household");
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const [invite, setInvite] = useState<HouseholdInvite | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    householdStore.saveState.reset();
    void householdStore.readInvite(code).then((result) => {
      if (!current) return;
      setInvite(result.invite ?? null);
      setError(result.error ?? null);
    });
    return () => {
      current = false;
    };
  }, [householdStore, code]);

  const join = async () => {
    if (await householdStore.join(code)) void navigate("/settings");
  };

  return (
    <main className="flex flex-grow items-center justify-center py-6 md:py-10">
      <Card className="flex w-full max-w-md flex-col gap-5 p-5 md:p-8">
        <h1 className="m-0 text-xl font-semibold">{t("join.title")}</h1>
        {error ? (
          <>
            <Note tone="error">{error}</Note>
            <Link to="/" className="font-medium text-primary hover:underline">
              {t("join.dashboard")}
            </Link>
          </>
        ) : !invite ? (
          <p className="m-0 text-md text-muted-foreground">{t("join.opening")}</p>
        ) : (
          <>
            <p className="m-0 text-base text-foreground">
              <Trans
                t={t}
                i18nKey={invite.member_count > 1 ? "join.invitesWithMembers" : "join.invites"}
                values={{ owner: invite.owner_name, name: invite.name }}
                count={invite.member_count > 1 ? invite.member_count : undefined}
                components={{ b: <strong className="break-words" /> }}
              />
            </p>
            <ul className="m-0 flex list-disc flex-col gap-2 pl-5 text-md leading-relaxed text-muted-foreground">
              <li>{t("join.shared")}</li>
              <li>{t("join.private")}</li>
              <li>{t("join.yours")}</li>
            </ul>
            {householdStore.saveState.error && (
              <Note tone="error">{householdStore.saveState.error}</Note>
            )}
            <div className="flex flex-col-reverse gap-2 md:flex-row md:justify-end">
              <Button
                type="button"
                variant="ghost"
                className="min-h-11 w-full md:w-auto"
                onClick={() => void navigate("/")}
              >
                {t("join.notNow")}
              </Button>
              <Button
                type="button"
                variant="primary"
                className="min-h-11 w-full md:w-auto"
                disabled={householdStore.saveState.isLoading}
                onClick={() => void join()}
              >
                {t("join.join", { name: invite.name })}
              </Button>
            </div>
          </>
        )}
      </Card>
    </main>
  );
});
