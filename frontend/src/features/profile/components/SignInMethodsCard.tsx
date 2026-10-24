import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { KeyRound } from "lucide-react";
import { useTranslation } from "react-i18next";

import { dateFormat } from "@/i18n/format";
import { device } from "@/platform";
import { Button, Note, Pill } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { SignInProvider } from "@/stores/SignInStore";

const NAMES: Record<SignInProvider, string> = { google: "Google", apple: "Apple" };

/**
 * The providers that sign in to the account (F1.6.2): each linked one with the address it
 * holds and an Unlink, each switched-on one not linked yet with a Link. An account opened
 * with a provider has no password until it asks for a link to set one — and cannot unlink
 * its last provider before that. Shown only when a provider is on or linked.
 */
export const SignInMethodsCard = observer(function SignInMethodsCard() {
  const { signInStore, authStore, accountStore, toastStore } = useStores();
  const { t } = useTranslation("profile");
  const { t: say } = useTranslation("messages");
  const user = authStore.user;

  useEffect(() => {
    void signInStore.loadProviders();
    void signInStore.loadIdentities();
  }, [signInStore]);

  const linked = new Map(signInStore.identities.map((i) => [i.provider, i]));
  // Linking leaves for the provider's page, which the store apps cannot open yet.
  const linkable = device.isApp ? [] : signInStore.available.filter((p) => !linked.has(p));
  if (!user || (linked.size === 0 && linkable.length === 0)) return null;
  const date = dateFormat({ day: "numeric", month: "short", year: "numeric" });

  return (
    <li className="flex flex-col gap-2.5 px-4 py-3">
      <div className="flex min-h-11 items-center gap-3">
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-chip bg-tone-primary-bg text-primary"
        >
          <KeyRound size={18} />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-lg font-bold">{t("signInMethods.title")}</span>
          <span className="text-sm text-muted-foreground">{t("signInMethods.hint")}</span>
        </span>
      </div>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {[...linked.values()].map((identity) => (
          <li
            key={identity.provider}
            className="flex flex-col gap-2 rounded-control bg-surface p-3 md:flex-row md:items-center"
          >
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="flex items-center gap-2 font-semibold">
                {NAMES[identity.provider]}
                <Pill tone="success" size="sm">
                  {t("signInMethods.linked")}
                </Pill>
              </span>
              <span className="truncate text-sm text-muted-foreground">
                {[identity.email, date.format(new Date(identity.created_at))]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="w-full md:w-auto"
              onClick={() => {
                void signInStore.unlink(identity.provider);
              }}
            >
              {t("signInMethods.unlink")}
            </Button>
          </li>
        ))}
        {linkable.map((provider) => (
          <li
            key={provider}
            className="flex flex-col gap-2 rounded-control bg-surface p-3 md:flex-row md:items-center"
          >
            <span className="flex-1 font-semibold">{NAMES[provider]}</span>
            <Button
              type="button"
              size="sm"
              className="w-full md:w-auto"
              onClick={() => {
                signInStore.start(provider, "link");
              }}
            >
              {t("signInMethods.link")}
            </Button>
          </li>
        ))}
      </ul>
      {!user.has_password && (
        <Note tone="info">
          <span className="flex flex-col gap-2 md:flex-row md:items-center">
            <span className="flex-1">{t("signInMethods.noPassword")}</span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="w-full md:w-auto"
              onClick={() => {
                void accountStore.forgotPassword(user.email).then(() => {
                  toastStore.showSuccess(say("profile.passwordLinkSent"));
                });
              }}
            >
              {t("signInMethods.setPassword")}
            </Button>
          </span>
        </Note>
      )}
    </li>
  );
});
