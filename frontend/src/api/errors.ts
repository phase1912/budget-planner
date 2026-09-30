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

/** What a request that never reached an answer reports, read like any server error. */
export const UNREACHABLE = {
  detail: "The server could not be reached. Try again in a moment.",
} as const;

/**
 * Send a request that never throws: a network failure, or a response the browser
 * refused to read (a server error without CORS headers), comes back as `error`
 * like any other failure. openapi-fetch throws in those cases, which would
 * otherwise escape the store and leave the screen silently unchanged.
 */
export async function settle<T extends { error?: unknown }>(
  send: () => Promise<T>,
): Promise<T | { data?: undefined; error: typeof UNREACHABLE }> {
  try {
    return await send();
  } catch {
    return { error: UNREACHABLE };
  }
}
