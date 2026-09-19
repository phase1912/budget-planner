/**
 * Pull a human message out of whichever error envelope the API used.
 *
 * The backend answers RFC 7807 (`{title, status, detail, code}`) where `detail`
 * is a sentence, but FastAPI's own request validation answers
 * `{detail: [{msg}]}`. Reading only the latter — as the stores used to — threw
 * away every message the server actually wrote, leaving the user with a generic
 * fallback in place of the reason.
 */
export function errorMessage(error: unknown, fallback: string): string {
  const envelope = error as { detail?: string | { msg?: string }[]; title?: string };

  if (typeof envelope.detail === "string") return envelope.detail;

  const validationMessage = Array.isArray(envelope.detail) ? envelope.detail[0]?.msg : undefined;
  if (typeof validationMessage === "string") return validationMessage;

  if (typeof envelope.title === "string") return envelope.title;

  return fallback;
}
