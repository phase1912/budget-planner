import { observer } from "mobx-react-lite";
import { useEffect } from "react";
import { useStores } from "@/stores/StoreContext";

export const ToastContainer = observer(function ToastContainer() {
  const { toastStore } = useStores();
  const { toast } = toastStore;

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        toastStore.clearToast();
      }, 5000);
      return () => {
        clearTimeout(timer);
      };
    }
  }, [toast, toastStore]);

  if (!toast) return null;

  const bgClass =
    toast.type === "error"
      ? "bg-tone-error-bg text-tone-error-text border-tone-error-border"
      : "bg-tone-success-bg text-tone-success-text border-tone-success-border";

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-5 duration-300">
      <div
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
