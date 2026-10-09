import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button, Card, Note } from "@/shared/components";
import type { HouseholdInvite } from "@/stores/HouseholdStore";
import { useStores } from "@/stores/StoreContext";

/**
 * Where an invite link lands (E12 — F12.3, ADR-0017): whose household it is, what joining
 * shares, and a Join button. A visitor who is not signed in is sent to sign in or register
 * first and brought back here by ProtectedRoute.
 */
export const JoinHouseholdPage = observer(function JoinHouseholdPage() {
  const { householdStore } = useStores();
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
    if (await householdStore.join(code)) void navigate("/profile");
  };

  return (
    <main className="flex flex-grow items-center justify-center py-6 md:py-10">
      <Card className="flex w-full max-w-md flex-col gap-5 p-5 md:p-8">
        <h1 className="m-0 text-xl font-semibold">Join a household</h1>
        {error ? (
          <>
            <Note tone="error">{error}</Note>
            <Link to="/" className="font-medium text-primary hover:underline">
              Go to your dashboard
            </Link>
          </>
        ) : !invite ? (
          <p className="m-0 text-md text-muted-foreground">Opening the invite…</p>
        ) : (
          <>
            <p className="m-0 text-base text-foreground">
              <strong>{invite.owner_name}</strong> invites you to{" "}
              <strong className="break-words">{invite.name}</strong>
              {invite.member_count > 1 ? `, with ${String(invite.member_count)} members` : ""}.
            </p>
            <ul className="m-0 flex list-disc flex-col gap-2 pl-5 text-md leading-relaxed text-muted-foreground">
              <li>You will keep one budget together and see each other&apos;s receipts.</li>
              <li>
                Mark a receipt private and the household sees only its amount, in a monthly sum.
              </li>
              <li>Only you can change your receipts, and you can leave at any time.</li>
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
                Not now
              </Button>
              <Button
                type="button"
                variant="primary"
                className="min-h-11 w-full md:w-auto"
                disabled={householdStore.saveState.isLoading}
                onClick={() => void join()}
              >
                Join {invite.name}
              </Button>
            </div>
          </>
        )}
      </Card>
    </main>
  );
});
