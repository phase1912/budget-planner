import { Link } from "react-router-dom";
import { Stack, Button } from "@/shared/components";

export const NotFoundScreen = () => {
  return (
    <div className="flex-grow flex items-center justify-center">
      <Stack className="gap-4 text-center items-center">
        <h1 className="text-xl font-bold">404 - Page Not Found</h1>
        <p className="text-md text-muted-foreground">The page you are looking for doesn't exist.</p>
        <Link to="/" className="mt-4 contents">
          <Button variant="secondary">Return Home</Button>
        </Link>
      </Stack>
    </div>
  );
};
