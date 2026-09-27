import { Outlet, useLocation } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { Container } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { BottomNavigation } from "./BottomNavigation";
import { Header } from "./Header";
import { ToastContainer } from "@/shared/components/Toast/Toast";

/**
 * The frame every screen renders inside: header, content and, on a phone, the
 * bottom navigation (F9.4, F6.7). The upload flow is a focused task with its own
 * way back, so it goes without the bar, as docs/design/screens/upload-mobile.html does.
 */
export const AppShell = observer(() => {
  const { authStore } = useStores();
  const { pathname } = useLocation();
  const withBottomBar = authStore.isAuthenticated && !pathname.startsWith("/upload");
  return (
    <div className="flex flex-col min-h-screen bg-muted text-foreground">
      <Header />
      <ToastContainer />

      <main
        className={`flex-grow overflow-hidden flex flex-col md:p-8 ${withBottomBar ? "pb-24" : ""}`}
      >
        <Container className="flex-grow flex flex-col">
          <Outlet />
        </Container>
      </main>
      {withBottomBar && <BottomNavigation />}
    </div>
  );
});
