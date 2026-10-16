/** Where the backend answers; set per environment at build time (F0.9). */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
