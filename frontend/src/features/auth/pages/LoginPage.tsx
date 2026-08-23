import * as React from "react";
import { observer } from "mobx-react-lite";
import { useNavigate, Link } from "react-router-dom";
import { useStores } from "@/stores/StoreContext";
import { Button, Input, Card } from "@/shared/components";

export const LoginPage = observer(() => {
  const { authStore } = useStores();
  const navigate = useNavigate();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");

  const handleSubmit = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    const success = await authStore.login({ email, password });
    if (success) {
      await navigate("/");
    }
  };

  return (
    <div className="flex-grow flex items-center justify-center py-10">
      <Card className="w-full max-w-md p-8 flex flex-col gap-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">Welcome Back</h1>
          <p className="text-base text-muted-foreground">Sign in to your account</p>
        </div>

        {authStore.authState.error && (
          <div
            role="alert"
            className="p-4 bg-tone-error-bg border border-tone-error-border text-tone-error-text rounded-control"
          >
            {authStore.authState.error}
          </div>
        )}

        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="flex flex-col gap-5"
        >
          <Input
            id="email"
            type="email"
            label="Email address"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
            }}
            required
            placeholder="you@example.com"
          />
          <Input
            id="password"
            type="password"
            label="Password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
            }}
            required
          />

          <Button type="submit" size="lg" disabled={authStore.authState.isLoading} className="mt-2">
            {authStore.authState.isLoading ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <div className="text-center text-base mt-2">
          <span className="text-muted-foreground">Don't have an account? </span>
          <Link to="/register" className="text-primary hover:underline font-medium">
            Register here
          </Link>
        </div>
      </Card>
    </div>
  );
});
