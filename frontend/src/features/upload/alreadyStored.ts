/** The receipt a photo turned out to be a copy of, as the server reported it (F11.5). */
export interface AlreadyStored {
  receipt_id: string;
  created_at: string;
  merchant_name?: string | null;
}

/**
 * Why a receipt in the wizard will not be stored: its fiscal numbers match one the user
 * already has (ADR-0015), so it is the same receipt, and when that one was added.
 * `created_at` is a real instant, so it is shown in the browser's own timezone.
 */
export function alreadyStoredText(stored: AlreadyStored, merchant?: string | null): string {
  const name = merchant ?? stored.merchant_name ?? "This receipt";
  const added = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long" }).format(
    new Date(stored.created_at),
  );
  return `${name} is already stored — you added it on ${added}. It will not be stored again.`;
}
