import { StrictMode } from "react";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router";

import { App } from "@/App";
import i18n from "@/i18n";
import type { Language } from "@/i18n/languages";
import { StoreProvider } from "@/stores/StoreContext";

/**
 * A public page as HTML, built once at build time (F17.2): the same tree the browser
 * renders, for a visitor without a session, at `path`, in `language`. scripts/prerender.mjs
 * writes it into the page so search engines and link previews read it without running
 * the app; the browser then renders its own copy in the reader's language and theme.
 */
export async function render(path: string, language: Language): Promise<string> {
  await i18n.changeLanguage(language);
  return renderToString(
    <StrictMode>
      <StoreProvider>
        <StaticRouter location={path}>
          <App />
        </StaticRouter>
      </StoreProvider>
    </StrictMode>,
  );
}
