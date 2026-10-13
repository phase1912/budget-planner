import type { components } from "@/api/schema";
import i18n from "@/i18n";

type Receipt = Pick<
  components["schemas"]["ReceiptResponse"],
  "channel" | "source_reference" | "file_ids"
>;

/**
 * How a receipt reached the user's record, in words (BRD A12, A15 — F11.1.5), and the
 * reference that identifies its source, if the channel keeps one: the email's Message-ID.
 * A support question about a wrong figure starts from here.
 */
export function receiptSource(receipt: Receipt): { label: string; reference: string | null } {
  const photos = receipt.file_ids.length;
  const label =
    receipt.channel === "email"
      ? i18n.t("receipts:source.email")
      : receipt.channel === "qr"
        ? i18n.t("receipts:source.qr")
        : i18n.t("receipts:source.photos", { count: photos });
  const reference = receipt.source_reference?.replace(/^<|>$/g, "").trim() ?? "";
  return { label, reference: reference === "" ? null : reference };
}
