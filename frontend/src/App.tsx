import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { AppShell } from "@/features/app-shell/AppShell";
import { PublicLandingPage } from "@/features/public-landing/pages/PublicLandingPage";
import { NotFoundPage } from "@/features/public-landing/pages/NotFoundPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { ProfilePage } from "@/features/profile/pages/ProfilePage";
import { UploadPage } from "@/features/upload/pages/UploadPage";

export const App = observer(function App() {
  const { authStore } = useStores();
  const isAuthenticated = authStore.isAuthenticated;

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={isAuthenticated ? <DashboardPage /> : <PublicLandingPage />} />
          <Route
            path="/login"
            element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
          />
          <Route
            path="/register"
            element={isAuthenticated ? <Navigate to="/" replace /> : <RegisterPage />}
          />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            {/* Placeholders for upcoming features (prevents 404s on navigation) */}
            <Route path="/receipts" element={<DashboardPage />} />
            <Route path="/categories" element={<DashboardPage />} />
            <Route path="/statistics" element={<DashboardPage />} />
            <Route path="/goals" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
});
