import { Routes, Route, Navigate } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { AppShell } from "@/features/app-shell/AppShell";
import { PublicLandingPage } from "@/features/public-landing/pages/PublicLandingPage";
import { NotFoundPage } from "@/features/public-landing/pages/NotFoundPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { ConfirmLinkPage } from "@/features/auth/pages/ConfirmLinkPage";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { ProfilePage } from "@/features/profile/pages/ProfilePage";
import { UploadPage } from "@/features/upload/pages/UploadPage";
import { ReceiptsPage } from "@/features/receipts/pages/ReceiptsPage";
import { CategoriesPage } from "@/features/categories/pages/CategoriesPage";
import { CategorisationQueuePage } from "@/features/categories/pages/CategorisationQueuePage";
import { GoalsPage } from "@/features/goals/pages/GoalsPage";
import { StatisticsPage } from "@/features/statistics/pages/StatisticsPage";
import { ProductsPage } from "@/features/products/pages/ProductsPage";
import { TripPage } from "@/features/trips/pages/TripPage";
import { TripsPage } from "@/features/trips/pages/TripsPage";
import { JoinHouseholdPage } from "@/features/household/pages/JoinHouseholdPage";
import { LANGUAGES } from "@/i18n/languages";

/**
 * Every route of the product. The router itself is the caller's: the browser's in
 * main.tsx, a static one when the public pages are prerendered (F17.2).
 */
export const App = observer(function App() {
  const { authStore } = useStores();
  const isAuthenticated = authStore.isAuthenticated;

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={isAuthenticated ? <DashboardPage /> : <PublicLandingPage />} />
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
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/confirm-email" element={<ConfirmLinkPage kind="address" />} />
        <Route path="/confirm-email-change" element={<ConfirmLinkPage kind="change" />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/receipts" element={<ReceiptsPage />} />
          <Route path="/categories/manage" element={<CategoriesPage />} />
          <Route path="/categories" element={<CategorisationQueuePage />} />
          {/* Placeholders for upcoming features (prevents 404s on navigation) */}
          <Route path="/statistics" element={<StatisticsPage />} />
          <Route path="/statistics/products" element={<ProductsPage />} />
          <Route path="/trips" element={<TripsPage />} />
          <Route path="/trips/:id" element={<TripPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/join/:code" element={<JoinHouseholdPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
});
