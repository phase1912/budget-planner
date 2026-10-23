import type { CapacitorConfig } from "@capacitor/cli";

/**
 * The store apps (E22, E25): the same build as the website, served from the device.
 *
 * The id is permanent once a store has published it. Android serves the app from
 * https://localhost and iOS from capacitor://localhost; both are in the API's CORS list.
 */
const config: CapacitorConfig = {
  appId: "app.budgetagent",
  appName: "Budget Agent",
  webDir: "dist",
  ios: {
    // The web view reaches under the notch and the home indicator; safe areas pad it.
    contentInset: "never",
  },
  plugins: {
    // Edge to edge on Android too (Android 15 enforces it): the device's insets reach the
    // page as env(safe-area-inset-*), which the shell pads by (F22.5.1, F25.2.1).
    SystemBars: {
      insetsHandling: "css",
    },
    SplashScreen: {
      launchAutoHide: false,
      // Midnight's ground, the default look, so the splash hands over without a flash.
      backgroundColor: "#0b1222",
    },
  },
};

export default config;
