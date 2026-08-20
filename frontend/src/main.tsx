import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/App";
import "@/shared/styles/index.css";
import { StoreProvider } from "@/stores/StoreContext";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(container).render(
  <StrictMode>
    <StoreProvider>
      <App />
    </StoreProvider>
  </StrictMode>,
);
