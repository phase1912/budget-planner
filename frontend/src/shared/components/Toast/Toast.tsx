import { observer } from "mobx-react-lite";
import { useEffect } from "react";
import { useStores } from "@/stores/StoreContext";

export const ToastContainer = observer(function ToastContainer() {
  const { toastStore } = useStores();
  const { toast } = toastStore;

  useEffect(() => {
    if (toast) {
      // Capture the current toast reference
      const currentToast = toast;
      const timer = setTimeout(() => {
        // Only clear if the store's toast is still the same one we started the timer for
        if (toastStore.toast === currentToast) {
          toastStore.clearToast();
        }
      }, 5000);
      return () => {
        clearTimeout(timer);
      };
    }
  }, [toast, toastStore]);

  if (!toast) return null;

  let bgClass = "bg-tone-info-bg text-tone-info-text border-tone-info-border";
  if (toast.type === "error") {
    bgClass = "bg-tone-error-bg text-tone-error-text border-tone-error-border";
  } else if (toast.type === "success") {
    bgClass = "bg-tone-success-bg text-tone-success-text border-tone-success-border";
  }

  const role = toast.type === "error" ? "alert" : "status";

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-5 duration-300">
      <div
        role={role}
        aria-atomic="true"
        className={`px-4 py-3 rounded-control border shadow-lg max-w-md w-full flex items-center justify-between gap-4 ${bgClass}`}
      >
        <p className="text-base font-medium">{toast.message}</p>
        <button
          onClick={() => {
            toastStore.clearToast();
          }}
          className="opacity-70 hover:opacity-100 transition-opacity"
          aria-label="Close"
        >
          ✕
        </button>
      </div>
    </div>
  );
});
