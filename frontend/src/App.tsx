import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "@/features/app-shell/AppShell";
import { PublicLandingScreen } from "@/features/public-landing/PublicLandingScreen";
import { NotFoundScreen } from "@/features/public-landing/NotFoundScreen";
import { LoginScreen, RegisterScreen } from "@/features/public-landing/PlaceholderScreens";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<PublicLandingScreen />} />
          <Route path="/login" element={<LoginScreen />} />
          <Route path="/register" element={<RegisterScreen />} />
          <Route path="*" element={<NotFoundScreen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
