import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { Container } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { BottomNavigation } from "./BottomNavigation";
import { SideNavigation } from "./SideNavigation";
import { Header } from "./Header";
import { ServerWakingNotice } from "./ServerWakingNotice";
import { ConfirmEmailBanner } from "./ConfirmEmailBanner";
import { ToastContainer } from "@/shared/components/Toast/Toast";

/**
 * The frame every screen renders inside (F9.4, F23.2): the header, then the content with,
 * for a signed-in user, the navigation — a bar along the bottom on a phone, a side menu on
 * wider screens. On a phone the upload flow is a focused task with its own way back, so it
 * goes without the bar.
 */
export const AppShell = observer(() => {
  const { authStore, analyticsStore } = useStores();
  const { pathname, search } = useLocation();
  // Each public page opened is counted, without anything about the reader (F17.3.2).
  useEffect(() => {
    analyticsStore.countView(pathname, document.referrer, search, authStore.isAuthenticated);
  }, [analyticsStore, authStore, pathname, search]);
  const signedIn = authStore.isAuthenticated;
  const withBottomBar = signedIn && !pathname.startsWith("/upload");
  return (
    <div className="flex flex-col min-h-screen bg-muted text-foreground">
      <Header />
      <ToastContainer />
      <ServerWakingNotice />

      <div className="flex flex-grow">
        {signedIn && <SideNavigation />}
        <main
          className={`flex min-w-0 flex-grow flex-col overflow-clip md:p-8 ${withBottomBar ? "pb-24 md:pb-8" : ""}`}
        >
          <Container className="flex-grow flex flex-col">
            <ConfirmEmailBanner />
            <Outlet />
          </Container>
        </main>
      </div>
      {withBottomBar && <BottomNavigation />}
    </div>
  );
});
