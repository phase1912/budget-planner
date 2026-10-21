import type { ReactNode } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Check, X, type LucideIcon } from "lucide-react";

import { Button } from "@/shared/components";
import type { ChatMessage } from "@/stores/AssistantStore";
import { useStores } from "@/stores/StoreContext";

/**
 * The frame every proposed action shares (F21.7.1): what it is, its fields, and Approve or
 * Cancel while it waits — or, once done, whether it was saved and where to see it.
 */
export const CardShell = observer(function CardShell({
  message,
  title,
  icon: Icon,
  busy,
  onApprove,
  done,
  children,
}: {
  message: ChatMessage;
  title: string;
  icon: LucideIcon;
  busy: boolean;
  onApprove: () => void;
  /** What a saved card says under its fields: the sum, a way to the screen. */
  done?: ReactNode;
  children: ReactNode;
}) {
  const { assistantStore } = useStores();
  const { t } = useTranslation("assistant");
  const proposed = message.card_state === "proposed";
  return (
    <article
      aria-label={title}
      className="on-surface flex flex-col gap-3 rounded-card border-2 border-primary bg-surface p-4"
    >
      <span className="flex items-center gap-2.5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
          <Icon size={18} aria-hidden="true" />
        </span>
        <span className="min-w-0 text-lg font-extrabold">{title}</span>
        {!proposed && (
          <span className="ml-auto shrink-0 rounded-pill bg-muted px-2 py-0.5 text-xs font-extrabold">
            {message.card_state === "saved" ? t("card.saved") : t("card.dismissed")}
          </span>
        )}
      </span>
      {children}
      {proposed ? (
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="secondary"
            className="min-h-11"
            disabled={busy}
            onClick={() => void assistantStore.dismiss(message)}
          >
            <X size={16} aria-hidden="true" />
            {t("card.dismiss")}
          </Button>
          <Button className="min-h-11" disabled={busy} onClick={onApprove}>
            <Check size={16} aria-hidden="true" />
            {t("card.approve")}
          </Button>
        </div>
      ) : (
        message.card_state === "saved" && done
      )}
    </article>
  );
});
