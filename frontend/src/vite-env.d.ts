/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL the generated API client sends requests to (F9.3.2). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
