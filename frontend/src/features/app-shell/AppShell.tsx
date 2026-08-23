import { Outlet } from "react-router-dom";
import { observer } from "mobx-react-lite";
import { Container } from "@/shared/components";
import { Header } from "./Header";
import { ToastContainer } from "@/shared/components/Toast/Toast";

export const AppShell = observer(() => {
  return (
    <div className="flex flex-col min-h-screen bg-muted text-foreground">
      <Header />
      <ToastContainer />

      <main className="flex-grow overflow-hidden p-8 flex flex-col">
        <Container className="flex-grow flex flex-col">
          <Outlet />
        </Container>
      </main>
    </div>
  );
});
