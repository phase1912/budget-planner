import * as React from "react";
import { observer } from "mobx-react-lite";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useStores } from "@/stores/StoreContext";
import { Button, Input, Card, Note } from "@/shared/components";
import { PasswordChecklist } from "../components/PasswordChecklist";
import { passwordIsValid } from "../passwordRules";
import { useTranslation } from "react-i18next";
import { screenLanguage } from "@/i18n/languages";

export const RegisterPage = observer(() => {
  const { authStore, serverStore } = useStores();
  // The server may be asleep: start it while the form is being filled in.
  React.useEffect(() => {
    serverStore.wake();
  }, [serverStore]);
  const { t, i18n } = useTranslation("auth");
  const navigate = useNavigate();
  const location = useLocation();
  // Where the visitor was going before being asked to sign in — an invite link (F12.3).
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [firstName, setFirstName] = React.useState("");
  const [lastName, setLastName] = React.useState("");
  const [passwordError, setPasswordError] = React.useState("");

  const handleSubmit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setPasswordError("");

    if (password !== confirmPassword) {
      setPasswordError(t("register.mismatch"));
      return;
    }

    const success = await authStore.register({
      email,
      password,
      first_name: firstName,
      last_name: lastName,
      // The confirmation letter is written in the language of this screen (F17.8.1).
      language: screenLanguage(i18n.language),
    });
    if (success) {
      await navigate(from, { replace: true });
    }
  };

  return (
    <div className="flex-grow flex items-center justify-center py-10">
      <Card className="w-full max-w-md p-8 flex flex-col gap-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">{t("register.title")}</h1>
          <p className="text-base text-muted-foreground">{t("register.subtitle")}</p>
        </div>

        {authStore.authState.error && <Note tone="error">{authStore.authState.error}</Note>}

        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="flex flex-col gap-5"
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Input
              id="firstName"
              type="text"
              label={t("fields.firstName")}
              value={firstName}
              onChange={(e) => {
                setFirstName(e.target.value);
              }}
              required
            />
            <Input
              id="lastName"
              type="text"
              label={t("fields.lastName")}
              value={lastName}
              onChange={(e) => {
                setLastName(e.target.value);
              }}
              required
            />
          </div>
          <Input
            id="email"
            type="email"
            label={t("fields.email")}
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
            }}
            required
            placeholder={t("fields.emailPlaceholder")}
          />
          <Input
            id="password"
            type="password"
            label={t("fields.password")}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
            }}
            required
            minLength={8}
          />
          <Input
            id="confirmPassword"
            type="password"
            label={t("fields.confirmPassword")}
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
            }}
            required
            minLength={8}
            error={passwordError}
          />
          <PasswordChecklist password={password} confirm={confirmPassword} />

          <Button
            type="submit"
            size="lg"
            disabled={
              authStore.authState.isLoading ||
              !passwordIsValid(password) ||
              password !== confirmPassword
            }
            className="mt-2"
          >
            {authStore.authState.isLoading ? t("register.submitting") : t("register.submit")}
          </Button>
        </form>

        <div className="text-center text-base mt-2">
          <span className="text-muted-foreground">{t("register.haveAccount")} </span>
          <Link
            to="/login"
            state={location.state as unknown}
            className="text-primary hover:underline font-medium"
          >
            {t("register.signIn")}
          </Link>
        </div>
      </Card>
    </div>
  );
});
