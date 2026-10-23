import { useId, useState } from "react";
import { Flag } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button, Modal, ModalBody } from "@/shared/components";
import type { ChatMessage } from "@/stores/AssistantStore";
import { useStores } from "@/stores/StoreContext";

const REASONS = ["offensive", "wrong", "other"] as const;

/**
 * Reporting one assistant reply as offensive, wrong or otherwise (F22.4.2): the reply and
 * the reason go to the admins, nothing else of the conversation. Required of generative AI
 * apps by Google Play, and asked for by App Review.
 */
export function ReportReply({ message }: { message: ChatMessage }) {
  const { assistantStore } = useStores();
  const { t } = useTranslation("assistant");
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [reported, setReported] = useState(false);

  if (reported) {
    return <span className="px-1 text-sm text-muted-foreground">{t("report.done")}</span>;
  }
  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
        }}
        className="inline-flex min-h-11 items-center gap-1.5 self-start px-1 text-sm font-semibold text-muted-foreground hover:text-foreground"
      >
        <Flag size={13} aria-hidden="true" />
        {t("report.open")}
      </button>
      {open && (
        <Modal
          isOpen
          onClose={() => {
            setOpen(false);
          }}
          aria-labelledby={titleId}
          className="md:w-[420px]"
        >
          <ModalBody className="flex flex-col gap-3">
            <h2 id={titleId} className="m-0 text-[17px] font-bold">
              {t("report.title")}
            </h2>
            <p className="m-0 text-md text-muted-foreground">{t("report.hint")}</p>
            <div className="flex flex-col gap-2">
              {REASONS.map((reason) => (
                <Button
                  key={reason}
                  type="button"
                  variant="secondary"
                  className="min-h-11 justify-start"
                  onClick={() => {
                    setOpen(false);
                    void assistantStore.report(message, reason).then((done) => {
                      if (done) setReported(true);
                    });
                  }}
                >
                  {t(`report.reasons.${reason}`)}
                </Button>
              ))}
            </div>
          </ModalBody>
        </Modal>
      )}
    </>
  );
}
