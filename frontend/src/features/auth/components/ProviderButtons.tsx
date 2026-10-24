import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { device } from "@/platform";
import { useStores } from "@/stores/StoreContext";
import type { SignInProvider } from "@/stores/SignInStore";

/** Google's "G", in the colours its sign-in button rules require. */
function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.6 13.3l7.9 6.1C12.4 13.7 17.7 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.1 24.6c0-1.6-.1-3.1-.4-4.6H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17z"
      />
      <path
        fill="#FBBC05"
        d="M10.5 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C.9 16.6 0 20.2 0 24s.9 7.4 2.6 10.7l7.9-6.1z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.8 2.3-8.5 2.3-6.3 0-11.6-4.2-13.5-9.9l-7.9 6.1C6.6 42.6 14.6 48 24 48z"
      />
    </svg>
  );
}

/** Apple's logo, in the button's text colour as Apple's rules ask. */
function AppleMark() {
  return (
    <svg width="16" height="18" viewBox="0 0 814 1000" aria-hidden="true" fill="currentColor">
      <path d="M788 341c-6 4-108 62-108 190 0 148 130 200 134 202-1 3-21 72-69 142-43 62-88 124-156 124s-86-40-165-40c-77 0-104 41-166 41s-106-57-156-127C45 791 0 668 0 551c0-188 122-288 243-288 64 0 117 42 157 42 38 0 98-45 171-45 28 0 128 3 194 81zM554 159c30-36 52-86 52-136 0-7-1-14-2-20-49 2-108 33-143 74-28 32-54 82-54 133 0 8 1 15 2 18 3 1 9 2 14 2 44 0 99-30 131-71z" />
    </svg>
  );
}

/**
 * "Continue with Google" and "Continue with Apple" on the sign-in and sign-up pages
 * (F1.6.2), each only once the server says it is switched on. Not in the store apps yet:
 * Google refuses sign-in inside an app's web view, and App Review 4.8 wants Apple's
 * offered wherever Google's is.
 */
export const ProviderButtons = observer(function ProviderButtons() {
  const { signInStore } = useStores();
  const { t } = useTranslation("auth");

  useEffect(() => {
    if (!device.isApp) void signInStore.loadProviders();
  }, [signInStore]);

  if (device.isApp || signInStore.available.length === 0) return null;
  const label: Record<SignInProvider, string> = {
    google: t("providers.google"),
    apple: t("providers.apple"),
  };
  return (
    <div className="flex flex-col gap-3">
      {signInStore.available.map((provider) => (
        <button
          key={provider}
          type="button"
          onClick={() => {
            signInStore.start(provider);
          }}
          className={`flex min-h-11 w-full items-center justify-center gap-3 rounded-control px-4 text-lg font-semibold ${
            provider === "apple"
              ? "bg-foreground text-background"
              : "border border-border-strong bg-surface text-foreground"
          }`}
        >
          {provider === "google" ? <GoogleMark /> : <AppleMark />}
          {label[provider]}
        </button>
      ))}
      <p className="m-0 flex items-center gap-3 text-sm text-muted-foreground before:h-px before:flex-1 before:bg-border after:h-px after:flex-1 after:bg-border">
        {t("providers.or")}
      </p>
    </div>
  );
});
