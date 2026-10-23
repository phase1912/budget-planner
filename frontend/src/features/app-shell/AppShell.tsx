import { useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { Container } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { BottomNavigation } from "./BottomNavigation";
import { SideNavigation } from "./SideNavigation";
import { Header } from "./Header";
import { ServerWakingNotice } from "./ServerWakingNotice";
import { ConfirmEmailBanner } from "./ConfirmEmailBanner";
import { AiConsentDialog } from "@/features/ai-consent/AiConsentDialog";
import { ToastContainer } from "@/shared/components/Toast/Toast";
import { device } from "@/platform";

/**
 * The frame every screen renders inside (F9.4, F23.2): the header, then the content with,
 * for a signed-in user, the navigation — a bar along the bottom on a phone, a side menu on
 * wider screens. On a phone the upload flow is a focused task with its own way back, so it
 * goes without the bar.
 */
export const AppShell = observer(() => {
  const { authStore, analyticsStore, profileStore, themeStore } = useStores();
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  // In a store app (F22.2.1): the launch screen goes once the shell is drawn, and the
  // system back button walks back through the screens.
  useEffect(() => {
    void device.ready();
    return device.onBack(() => {
      void navigate(-1);
    });
  }, [navigate]);
  const dark = themeStore.theme === "dark";
  useEffect(() => {
    void device.setDarkBars(dark);
  }, [dark]);
  // Each public page opened is counted, without anything about the reader (F17.3.2).
  useEffect(() => {
    analyticsStore.countView(pathname, document.referrer, search, authStore.isAuthenticated);
  }, [analyticsStore, authStore, pathname, search]);
  const signedIn = authStore.isAuthenticated;
  // A profile cached before a field existed (onboarding, palette) is refreshed once.
  useEffect(() => {
    if (signedIn) void profileStore.loadProfile();
  }, [signedIn, profileStore]);
  const welcome = pathname === "/welcome";
  const withBottomBar = signedIn && !welcome && !pathname.startsWith("/upload");
  return (
    <div className="flex flex-col min-h-screen bg-muted text-foreground">
      {/* A solid strip under the status bar, so the page scrolls beneath it as in a native
          app; zero high wherever there is no bar to clear (F22.5.1, F25.2.1). */}
      <div aria-hidden="true" className="fixed inset-x-0 top-0 z-30 h-safe-top bg-muted" />
      {/* Signed in, every screen carries its own title (design v2); the header is the
          public pages'. */}
      {!signedIn && <Header />}
      <ToastContainer />
      <ServerWakingNotice />

      <div className="flex flex-grow">
        {signedIn && !welcome && <SideNavigation />}
        <main
          className={`flex min-w-0 flex-grow flex-col overflow-clip ${signedIn ? "pt-5 md:px-4 md:pt-8 lg:px-8" : "md:p-8"} ${withBottomBar ? "pb-28 md:pb-10" : ""}`}
        >
          <Container className="flex-grow flex flex-col">
            <ConfirmEmailBanner />
            {/* Asked once signed in, before any AI feature is used (F25.3.2). */}
            {signedIn && !welcome && <AiConsentDialog />}
            <Outlet />
          </Container>
        </main>
      </div>
      {withBottomBar && <BottomNavigation />}
    </div>
  );
});
