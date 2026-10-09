/**
 * Register the app's service worker (F9.8.2), in a production build only: under the
 * dev server it would cache what hot reloading is busy replacing.
 */
export function registerServiceWorker(): void {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").catch(() => {
      // An app that cannot install still works as a website; nothing to tell the user.
    });
  });
}
