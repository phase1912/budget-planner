import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";

export const DashboardPage = observer(function DashboardPage() {
  const { authStore } = useStores();

  return (
    <div className="flex-grow flex items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-xl font-semibold mb-4">Welcome back!</h1>
        <p className="text-lg text-muted-foreground">You are successfully authenticated.</p>
        <div className="mt-8">
          <p>Email: {authStore.user?.email}</p>
        </div>
      </div>
    </div>
  );
});
