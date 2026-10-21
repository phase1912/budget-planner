import { useEffect, useRef, useState } from "react";

import type { ChatMessage } from "@/stores/AssistantStore";
import { useStores } from "@/stores/StoreContext";

/**
 * Approving a card as the user left its fields (ADR-0025): a tap, or "approve" said while
 * it is the latest card waiting (F21.7). Only then is anything written.
 */
export function useApproval(
  message: ChatMessage,
  fields: Record<string, unknown>,
  today: string,
): { busy: boolean; approve: () => void } {
  const { assistantStore } = useStores();
  const [busy, setBusy] = useState(false);
  const approve = () => {
    setBusy(true);
    void assistantStore.save(message, fields, today).finally(() => {
      setBusy(false);
    });
  };
  const heard = useRef(assistantStore.approveSignal);
  useEffect(() => {
    if (assistantStore.approveSignal === heard.current) return;
    heard.current = assistantStore.approveSignal;
    if (assistantStore.waitingCard?.id === message.id) approve();
  });
  return { busy, approve };
}
