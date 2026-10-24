import { Routes, Route, Navigate } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { AppShell } from "@/features/app-shell/AppShell";
import { device } from "@/platform";
import { PublicLandingPage } from "@/features/public-landing/pages/PublicLandingPage";
import { NotFoundPage } from "@/features/public-landing/pages/NotFoundPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { ProviderCallbackPage } from "@/features/auth/pages/ProviderCallbackPage";
import { ConfirmLinkPage } from "@/features/auth/pages/ConfirmLinkPage";
import { LegalPage } from "@/features/legal/LegalPage";
import { HelpPage } from "@/features/help/HelpPage";
import { AdminDashboardPage } from "@/features/admin/AdminDashboardPage";
import { AdminLayout } from "@/features/admin/AdminLayout";
import { AdminReportsPage } from "@/features/admin/AdminReportsPage";
import { AdminLogPage } from "@/features/admin/AdminLogPage";
import { AdminUserPage } from "@/features/admin/AdminUserPage";
import { AdminUsersPage } from "@/features/admin/AdminUsersPage";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { ProfilePage } from "@/features/profile/pages/ProfilePage";
import { UploadPage } from "@/features/upload/pages/UploadPage";
import { ReceiptsPage } from "@/features/receipts/pages/ReceiptsPage";
import { CategoriesPage } from "@/features/categories/pages/CategoriesPage";
import { CategorisationQueuePage } from "@/features/categories/pages/CategorisationQueuePage";
import { GoalsPage } from "@/features/goals/pages/GoalsPage";
import { PlanPage } from "@/features/plan/PlanPage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";
import { StatisticsPage } from "@/features/statistics/pages/StatisticsPage";
import { ProductsPage } from "@/features/products/pages/ProductsPage";
import { ExplorePage } from "@/features/products/pages/ExplorePage";
import { TripPage } from "@/features/trips/pages/TripPage";
import { TripsPage } from "@/features/trips/pages/TripsPage";
import { JoinHouseholdPage } from "@/features/household/pages/JoinHouseholdPage";
import { AccountsPage } from "@/features/money-accounts/pages/AccountsPage";
import { AssistantPage } from "@/features/assistant/AssistantPage";
import { AccountPage } from "@/features/money-accounts/pages/AccountPage";
import { LANGUAGES } from "@/i18n/languages";

/**
 * Every route of the product. The router itself is the caller's: the browser's in
 * main.tsx, a static one when the public pages are prerendered (F17.2).
 */
export const App = observer(function App() {
  const { authStore } = useStores();
  const isAuthenticated = authStore.isAuthenticated;
  const home =
    authStore.user?.onboarded_at === null ? <Navigate to="/welcome" replace /> : <DashboardPage />;

  return (
    <Routes>
      <Route element={<AppShell />}>
        {/* A store app was installed by someone who knows what it is: it opens on signing
            in, not on the website's landing (F22.2.1). */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              home
            ) : device.isApp ? (
              <Navigate to="/login" replace />
            ) : (
              <PublicLandingPage />
            )
          }
        />
        {/* The landing at each language's own address, for search engines and links (F17.2). */}
        {LANGUAGES.map((language) => (
          <Route
            key={language}
            path={`/${language}`}
            element={
              isAuthenticated ? (
                <Navigate to="/" replace />
              ) : (
                <PublicLandingPage language={language} />
              )
            }
          />
        ))}
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
        />
        <Route
          path="/register"
          element={isAuthenticated ? <Navigate to="/" replace /> : <RegisterPage />}
        />
        {/* Reached from letters (F17.8), signed in or not: a letter may be read elsewhere. */}
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        {/* Google and Apple send the browser back here, signed in or linking (F1.6.2). */}
        <Route path="/auth/callback/:provider" element={<ProviderCallbackPage />} />
        <Route path="/privacy" element={<LegalPage document="privacy" />} />
        <Route path="/terms" element={<LegalPage document="terms" />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/confirm-email" element={<ConfirmLinkPage kind="address" />} />
        <Route path="/confirm-email-change" element={<ConfirmLinkPage kind="change" />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/receipts" element={<ReceiptsPage />} />
          <Route path="/categories/manage" element={<CategoriesPage />} />
          <Route path="/categories" element={<CategorisationQueuePage />} />
          <Route path="/spending" element={<StatisticsPage />} />
          <Route path="/statistics" element={<Navigate to="/spending" replace />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/products/explore" element={<ExplorePage />} />
          <Route path="/statistics/products" element={<Navigate to="/products" replace />} />
          <Route path="/plan" element={<PlanPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/accounts/:id" element={<AccountPage />} />
          <Route path="/trips" element={<TripsPage />} />
          <Route path="/trips/:id" element={<TripPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/welcome" element={<OnboardingPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/settings" element={<ProfilePage />} />
          <Route path="/profile" element={<Navigate to="/settings" replace />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboardPage />} />
            <Route path="users" element={<AdminUsersPage />} />
            <Route path="users/:id" element={<AdminUserPage />} />
            <Route path="log" element={<AdminLogPage />} />
            <Route path="reports" element={<AdminReportsPage />} />
          </Route>
          <Route path="/join/:code" element={<JoinHouseholdPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
});
