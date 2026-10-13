import i18n from "@/i18n";
import { dateFormat } from "@/i18n/format";

const DAY = dateFormat({ day: "numeric", month: "long", year: "numeric" });

/**
 * Pull a human message out of whichever error envelope the API used.
 *
 * The backend answers RFC 7807 (`{title, status, detail, code, params}`) where `detail`
 * is a sentence, but FastAPI's own request validation answers
 * `{detail: [{msg}]}`. Reading only the latter — as the stores used to — threw
 * away every message the server actually wrote, leaving the user with a generic
 * fallback in place of the reason.
 *
 * In Ukrainian or Polish the code is shown in translation, filled from `params`; the
 * server's English `detail` is kept for English and for a code with no translation
 * (F9.9.5).
 */
export function errorMessage(error: unknown, fallback: string): string {
  const envelope = error as {
    detail?: string | { msg?: string }[];
    title?: string;
    code?: string;
    params?: Record<string, string | number>;
  };

  const translated = inLanguage(envelope.code, envelope.params);
  if (translated) return translated;

  if (typeof envelope.detail === "string") return envelope.detail;

  const validationMessage = Array.isArray(envelope.detail) ? envelope.detail[0]?.msg : undefined;
  if (typeof validationMessage === "string") return validationMessage;

  if (typeof envelope.title === "string") return envelope.title;

  return fallback;
}

function inLanguage(
  code: string | undefined,
  params: Record<string, string | number> = {},
): string | null {
  if (!code || i18n.language === "en" || !i18n.exists(`errors:${code}`)) return null;
  // A date arrives as an ISO day ("resets_on"), to be written the way the language writes it.
  const values = Object.fromEntries(
    Object.entries(params).map(([key, value]) => [
      key,
      key.endsWith("_on") ? DAY.format(new Date(`${String(value)}T00:00:00`)) : value,
    ]),
  );
  return i18n.t(`errors:${code}` as "errors:not_found", values);
}

/** What a request that never reached an answer reports, read like any server error. */
export const UNREACHABLE = {
  code: "unreachable",
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
    const response = (await send()) as T | undefined;
    return response ?? { error: UNREACHABLE };
  } catch {
    return { error: UNREACHABLE };
  }
}
