import { Navigate, Outlet, useLocation } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";

/**
 * Lets only a signed-in user through; one who has not been through the first-sign-in
 * setup yet is taken there first (F23.9), wherever they were headed.
 */
export const ProtectedRoute = observer(function ProtectedRoute() {
  const { authStore } = useStores();
  const location = useLocation();

  if (!authStore.isAuthenticated) {
    // Redirect them to the /login page, but save the current location they were
    // trying to go to when they were redirected. This allows us to send them
    // along to that page after they login, which is a nicer user experience
    // than dropping them off on the home page.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (authStore.user?.onboarded_at === null && location.pathname !== "/welcome") {
    return <Navigate to="/welcome" replace />;
  }

  return <Outlet />;
});
