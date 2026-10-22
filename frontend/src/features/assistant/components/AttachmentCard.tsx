import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRight, Loader2, Paperclip } from "lucide-react";

import type { ChatMessage } from "@/stores/AssistantStore";
import { useStores } from "@/stores/StoreContext";

/**
 * Receipt files the user attached in the chat (F21.8.2), followed through their reading:
 * read by the same upload as the Add screen, then checked and saved there, where its
 * duplicate, total and discount questions already live. An older attachment just says
 * how many there were and opens the receipts.
 */
export const AttachmentCard = observer(function AttachmentCard({
  message,
}: {
  message: ChatMessage;
}) {
  const { uploadStore } = useStores();
  const { t } = useTranslation("assistant");
  const fields = message.card?.fields ?? {};
  const count = typeof fields.count === "number" ? fields.count : 0;
  const current = uploadStore.jobId === fields.job_id;
  const reading = current && uploadStore.uploadState.isLoading;
  const ready = current && !reading && uploadStore.extractedData !== null;

  return (
    <div className="flex max-w-full flex-col gap-2 self-end rounded-card bg-surface px-4 py-3">
      <p className="m-0 inline-flex items-center gap-2 text-md font-bold">
        {reading ? (
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
        ) : (
          <Paperclip size={16} aria-hidden="true" />
        )}
        {reading
          ? t("attachment.reading", { count })
          : ready
            ? t("attachment.ready")
            : t("attachment.sent", { count })}
      </p>
      {!reading && (
        <Link
          to={ready ? "/upload" : "/receipts"}
          className="inline-flex min-h-11 items-center gap-2 self-start rounded-pill bg-tone-primary-bg px-4 text-md font-bold text-primary no-underline"
        >
          {ready ? t("attachment.check") : t("attachment.open")}
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      )}
    </div>
  );
});
