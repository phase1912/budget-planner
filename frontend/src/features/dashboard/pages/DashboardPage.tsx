import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";
import { useStores } from "@/stores/StoreContext";
import { Camera, Upload } from "lucide-react";
import { Button, Card } from "@/shared/components";

export const DashboardPage = observer(function DashboardPage() {
  const { authStore } = useStores();

  const user = authStore.user;

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const greeting = user?.first_name ? `${getGreeting()}, ${user.first_name}` : getGreeting();
  const currency = user?.currency ?? "PLN";

  return (
    <div className="flex-grow flex flex-col items-center py-10 px-8">
      <div className="w-full max-w-[960px] flex flex-col gap-7">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-3xl font-bold">{greeting}</h1>
          <p className="text-lg text-muted-foreground">
            Nothing recorded yet — your first receipt starts the budget.
          </p>
        </div>

        <Card className="p-12 flex flex-col items-center gap-4 text-center">
          <div className="w-16 h-16 rounded-full bg-tone-success-bg text-tone-success-text flex items-center justify-center">
            <Camera size={30} strokeWidth={1.8} />
          </div>
          <div className="flex flex-col gap-1.5 max-w-[460px]">
            <h2 className="text-[19px] font-semibold">Photograph your first receipt</h2>
            <p className="text-[14px] text-muted-foreground">
              Merchant, date, every line item and the total are read off the photo. Long receipts
              can be shot in several overlapping frames — items caught twice are counted once.
            </p>
          </div>
          <Link to="/upload" className="contents">
            <Button size="lg" className="mt-2">
              <Upload size={16} className="mr-2" />
              Upload a receipt
            </Button>
          </Link>
        </Card>

        <section className="flex flex-col gap-3 mt-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-[17px] font-semibold">Your account</h2>
            <Link to="/profile" className="text-[14px] text-primary hover:underline">
              Edit preferences
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-5 flex flex-col gap-1.5">
              <span className="text-sm text-muted-foreground">Signed in as</span>
              <span className="text-[15px] font-semibold">{user?.email}</span>
            </Card>
            <Card className="p-5 flex flex-col gap-1.5">
              <span className="text-sm text-muted-foreground">Currency</span>
              <span className="text-[15px] font-semibold">{currency}</span>
            </Card>
            <Card className="p-5 flex flex-col gap-1.5">
              <span className="text-sm text-muted-foreground">Monthly limit</span>
              <span className="text-[15px] font-semibold tracking-tight">
                {user?.budget_limit ? `${user.budget_limit} ${currency}` : `Not set`}
              </span>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
});
