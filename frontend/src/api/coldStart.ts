import { API_BASE_URL } from "@/api/baseUrl";

/** A read still waiting after this long is most likely waiting for the server to start. */
export const SLOW_AFTER_MS = 5_000;

let slowReads = 0;
const slowListeners = new Set<(waiting: boolean) => void>();

/**
 * Be told whenever reads start or stop waiting unusually long, so the screen can say the
 * server is starting rather than spin unexplained. Returns the unsubscribe function.
 */
export function onSlowReads(listener: (waiting: boolean) => void): () => void {
  slowListeners.add(listener);
  return () => slowListeners.delete(listener);
}

/** Count a read starting (1) or stopping (-1) to wait unusually long. */
export function reportSlowRead(change: 1 | -1) {
  slowReads += change;
  for (const listener of slowListeners) listener(slowReads > 0);
}

/**
 * Start the server before the first real request needs it: from zero instances it takes
 * about 20 s to start, time better spent while the user is still typing a password.
 */
export function wakeServer(): void {
  void fetch(`${API_BASE_URL}/health`, { mode: "no-cors", credentials: "omit" }).catch(
    () => undefined,
  );
}
