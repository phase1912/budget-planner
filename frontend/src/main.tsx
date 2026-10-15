import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "@/App";
import "@/i18n";
import "@/shared/styles/index.css";
import { StoreProvider } from "@/stores/StoreContext";
import { registerServiceWorker } from "@/pwa/registerServiceWorker";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root not found in index.html");
}

// A public page arrives prerendered (F17.2): it is shown at once, then the app replaces it
// with the same page rendered here, in the reader's language and theme, and takes over.
createRoot(container).render(
  <StrictMode>
    <StoreProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StoreProvider>
  </StrictMode>,
);

registerServiceWorker();
