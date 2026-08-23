import { Link } from "react-router-dom";
import { Stack, Button } from "@/shared/components";

export const PublicLandingScreen = () => {
  return (
    <div className="flex-grow flex items-center justify-center">
      <Stack className="gap-6 max-w-[480px] text-center items-center">
        <h1 className="text-xl font-bold">Budgeting made simple with AI</h1>
        <p className="text-md text-muted-foreground mb-4">
          Upload receipt photos, and let the AI extract line items, categorize purchases, and track
          them against your budget goals automatically.
        </p>
        <Stack className="flex-row items-center gap-4">
          <Link to="/login" className="contents">
            <Button variant="secondary" size="lg">
              Sign In
            </Button>
          </Link>
          <Link to="/register" className="contents">
            <Button variant="primary" size="lg">
              Create Account
            </Button>
          </Link>
        </Stack>
      </Stack>
    </div>
  );
};
