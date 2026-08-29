import * as React from "react";
import { observer } from "mobx-react-lite";
import { useNavigate, Link } from "react-router-dom";
import { useStores } from "@/stores/StoreContext";
import { Button, Input, Card, Note } from "@/shared/components";

export const RegisterPage = observer(() => {
  const { authStore } = useStores();
  const navigate = useNavigate();

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
      await navigate("/");
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
          <div className="grid grid-cols-2 gap-4">
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

          <Button type="submit" size="lg" disabled={authStore.authState.isLoading} className="mt-2">
            {authStore.authState.isLoading ? "Creating account..." : "Register"}
          </Button>
        </form>

        <div className="text-center text-base mt-2">
          <span className="text-muted-foreground">Already have an account? </span>
          <Link to="/login" className="text-primary hover:underline font-medium">
            Sign in
          </Link>
        </div>
      </Card>
    </div>
  );
});
