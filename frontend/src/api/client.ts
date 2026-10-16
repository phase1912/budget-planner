import createClient from "openapi-fetch";

import { API_BASE_URL } from "@/api/baseUrl";
import { reportSlowRead, SLOW_AFTER_MS } from "@/api/coldStart";
import type { paths } from "@/api/schema";

/**
 * The one typed entry point into the backend (F9.3.2). A store receives this
 * client through its constructor rather than importing it as a singleton — see
 * the DI convention in src/stores/README.md — so tests can inject a stub instead
 * of hitting the network.
 *
 * No import may reach the backend any other way: this is the boundary the
 * generated OpenAPI client exists to enforce (docs/architecture/overview.md).
 */
export { API_BASE_URL };

/** How long a read waits for the server, a cold start included (about 20 s on Cloud Run). */
const READ_TIMEOUT_MS = 30_000;
/** A write may carry photos; it is given longer and never repeated, as it may have landed. */
const WRITE_TIMEOUT_MS = 120_000;

function timeoutSignal(own: AbortSignal, ms: number): AbortSignal | undefined {
  // Older Safari has neither: the request then waits as long as the browser lets it.
  if (typeof AbortSignal.timeout !== "function") return undefined;
  const timer = AbortSignal.timeout(ms);
  return typeof AbortSignal.any === "function" ? AbortSignal.any([own, timer]) : timer;
}

/**
 * `fetch` that gives up rather than waiting forever, and tries a failed read once more.
 *
 * An installed app on iPhone can resume with a request that never settles, which left
 * every screen loading until the app was reopened; a cold start can also answer 503
 * without CORS headers. A read that fails either way is repeated once, then reported.
 */
export async function patientFetch(request: Request): Promise<Response> {
  const read = request.method === "GET" || request.method === "HEAD";
  const attempt = () =>
    fetch(request.clone(), {
      signal: timeoutSignal(request.signal, read ? READ_TIMEOUT_MS : WRITE_TIMEOUT_MS),
    });
  // Only reads: an upload is slow for its own reasons, and is not the server starting.
  const waited = { long: false };
  const timer = read
    ? setTimeout(() => {
        waited.long = true;
        reportSlowRead(1);
      }, SLOW_AFTER_MS)
    : undefined;
  try {
    return await attempt();
  } catch (error) {
    if (!read || request.signal.aborted) throw error;
    return await attempt();
  } finally {
    clearTimeout(timer);
    if (waited.long) reportSlowRead(-1);
  }
}

export const apiClient = createClient<paths>({
  baseUrl: API_BASE_URL,
  fetch: patientFetch,
});

export type ApiClient = typeof apiClient;
