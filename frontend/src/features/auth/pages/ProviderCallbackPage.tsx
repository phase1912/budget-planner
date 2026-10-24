import * as React from "react";
import { observer } from "mobx-react-lite";
import { Trans, useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button, Card, Input, LoadingState, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { Finish, SignInProvider } from "@/stores/SignInStore";

/**
 * Where Google and Apple send the browser back (F1.6.2): the answer in the address's
 * fragment is checked and sent on, and what the server still needs is asked here — the
 * terms for a new account, or the password of the account the address already has.
 */
export const ProviderCallbackPage = observer(function ProviderCallbackPage() {
  const { signInStore } = useStores();
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const params = useParams();
  const provider: SignInProvider = params.provider === "apple" ? "apple" : "google";
  const [step, setStep] = React.useState<Finish | "working">("working");
  const [acceptTerms, setAcceptTerms] = React.useState(false);
  const [password, setPassword] = React.useState("");
  const started = React.useRef(false);

  const settle = React.useCallback(
    (outcome: Finish) => {
      const home = signInStore.mode === "link" ? "/settings" : "/";
      if (outcome === "signed-in") void navigate(home, { replace: true });
      else if (outcome === "second-factor") void navigate("/login", { replace: true });
      else setStep(outcome);
    },
    [navigate, signInStore],
  );

  React.useEffect(() => {
    // Once: the fragment is read and wiped, a second run would find nothing.
    if (started.current) return;
    started.current = true;
    const fragment = window.location.hash;
    window.history.replaceState(null, "", window.location.pathname);
    void signInStore.finish(provider, fragment).then(settle);
  }, [provider, settle, signInStore]);

  const submit = (event: React.SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const extra = step === "needs-terms" ? { accept_terms: true } : { password };
    void signInStore.answer(extra).then(settle);
  };

  return (
    <div className="flex flex-grow flex-col items-center justify-center gap-6 py-10">
      <Card className="flex w-full max-w-md flex-col gap-6 p-6 md:p-8">
        {step === "working" && <LoadingState title={t("providers.working")} />}
        {step === "failed" && (
          <>
            <Note tone="error">{signInStore.error ?? t("providers.cancelled")}</Note>
            <Link to="/login" className="text-center text-base text-primary hover:underline">
              {t("providers.back")}
            </Link>
          </>
        )}
        {(step === "needs-terms" || step === "needs-password") && (
          <form className="flex flex-col gap-5" onSubmit={submit}>
            <div className="text-center">
              <h1 className="mb-2 text-xl font-semibold">
                {step === "needs-terms" ? t("providers.termsTitle") : t("providers.passwordTitle")}
              </h1>
              <p className="m-0 text-base text-muted-foreground">
                {step === "needs-terms" ? t("providers.termsLead") : t("providers.passwordLead")}
              </p>
            </div>
            {signInStore.error && <Note tone="error">{signInStore.error}</Note>}
            {step === "needs-terms" ? (
              <label className="flex min-h-11 cursor-pointer items-start gap-2.5 text-base leading-relaxed">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 flex-shrink-0 accent-primary"
                  checked={acceptTerms}
                  onChange={(e) => {
                    setAcceptTerms(e.target.checked);
                  }}
                  required
                />
                <span>
                  <Trans
                    t={t}
                    i18nKey="register.acceptTerms"
                    components={{
                      terms: (
                        <Link
                          to="/terms"
                          target="_blank"
                          className="text-primary hover:underline"
                        />
                      ),
                      privacy: (
                        <Link
                          to="/privacy"
                          target="_blank"
                          className="text-primary hover:underline"
                        />
                      ),
                    }}
                  />
                </span>
              </label>
            ) : (
              <Input
                id="link-password"
                type="password"
                autoComplete="current-password"
                label={t("fields.password")}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                }}
                required
              />
            )}
            <Button
              type="submit"
              size="lg"
              disabled={
                signInStore.isWorking ||
                (step === "needs-terms" ? !acceptTerms : password.length === 0)
              }
            >
              {signInStore.isWorking ? t("providers.working") : t("providers.continue")}
            </Button>
            <Link to="/login" className="text-center text-base text-primary hover:underline">
              {t("providers.back")}
            </Link>
          </form>
        )}
      </Card>
    </div>
  );
});
