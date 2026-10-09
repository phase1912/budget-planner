import * as React from "react";
import { observer } from "mobx-react-lite";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useStores } from "@/stores/StoreContext";
import { Button, Input, Card, Note } from "@/shared/components";
import { PasswordChecklist } from "../components/PasswordChecklist";
import { passwordIsValid } from "../passwordRules";

export const RegisterPage = observer(() => {
  const { authStore } = useStores();
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
      setPasswordError("Passwords do not match");
      return;
    }

    const success = await authStore.register({
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    if (success) {
      await navigate(from, { replace: true });
    }
  };

  return (
    <div className="flex-grow flex items-center justify-center py-10">
      <Card className="w-full max-w-md p-8 flex flex-col gap-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">Create Account</h1>
          <p className="text-base text-muted-foreground">Start tracking your budget today</p>
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
              label="First Name"
              value={firstName}
              onChange={(e) => {
                setFirstName(e.target.value);
              }}
              required
            />
            <Input
              id="lastName"
              type="text"
              label="Last Name"
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
            minLength={8}
          />
          <Input
            id="confirmPassword"
            type="password"
            label="Confirm Password"
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
            {authStore.authState.isLoading ? "Creating account..." : "Register"}
          </Button>
        </form>

        <div className="text-center text-base mt-2">
          <span className="text-muted-foreground">Already have an account? </span>
          <Link
            to="/login"
            state={location.state as unknown}
            className="text-primary hover:underline font-medium"
          >
            Sign in
          </Link>
        </div>
      </Card>
    </div>
  );
});
