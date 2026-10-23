import { device } from "@/platform";

/**
 * Register the app's service worker (F9.8.2), in a production build of the website only:
 * under the dev server it would cache what hot reloading is busy replacing, and a store
 * app already has its files on the device (F22.2.1).
 */
export function registerServiceWorker(): void {
  if (!import.meta.env.PROD || device.isApp || !("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").catch(() => {
      // An app that cannot install still works as a website; nothing to tell the user.
    });
  });
}
