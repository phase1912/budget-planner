import * as React from "react";
import { observer } from "mobx-react-lite";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useStores } from "@/stores/StoreContext";
import { Button, Input, Card, Note } from "@/shared/components";
import { useTranslation } from "react-i18next";

export const LoginPage = observer(() => {
  const { authStore } = useStores();
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");

  interface LocationState {
    from?: { pathname: string };
  }
  const state = location.state as LocationState | null;
  const from = state?.from?.pathname ?? "/";

  const handleSubmit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    const success = await authStore.login({ email, password });
    if (success) {
      void navigate(from, { replace: true });
    }
  };

  return (
    <div className="flex-grow flex items-center justify-center py-10">
      <Card className="w-full max-w-md p-8 flex flex-col gap-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">{t("login.title")}</h1>
          <p className="text-base text-muted-foreground">{t("login.subtitle")}</p>
        </div>

        {authStore.authState.error && <Note tone="error">{authStore.authState.error}</Note>}

        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="flex flex-col gap-5"
        >
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
          />

          <Button type="submit" size="lg" disabled={authStore.authState.isLoading} className="mt-2">
            {authStore.authState.isLoading ? t("login.submitting") : t("login.submit")}
          </Button>
        </form>

        <div className="text-center text-base mt-2">
          <span className="text-muted-foreground">{t("login.noAccount")} </span>
          {/* Passed on, so registering instead still ends where sign-in would (F12.3). */}
          <Link
            to="/register"
            state={location.state as unknown}
            className="text-primary hover:underline font-medium"
          >
            {t("login.register")}
          </Link>
        </div>
      </Card>
    </div>
  );
});
