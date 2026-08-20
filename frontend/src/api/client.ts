import createClient from "openapi-fetch";

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
export const apiClient = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
});

export type ApiClient = typeof apiClient;
