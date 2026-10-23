import { App } from "@capacitor/app";
import { Capacitor } from "@capacitor/core";
import { SplashScreen } from "@capacitor/splash-screen";
import { StatusBar, Style } from "@capacitor/status-bar";

import type { Device } from "./device";

/** A store app on Android or iOS, through Capacitor's plugins. */
export function nativeDevice(): Device {
  const kind = Capacitor.getPlatform() === "ios" ? "ios" : "android";
  return {
    kind,
    isApp: true,
    ready: () => SplashScreen.hide(),
    onBack(goBack) {
      // History the router can go back through comes first; the first screen leaves.
      const listener = App.addListener("backButton", ({ canGoBack }) => {
        if (canGoBack) goBack();
        else void App.exitApp();
      });
      return () => {
        void listener.then((l) => l.remove());
      };
    },
    // Style.Dark is light text, for a dark ground.
    setDarkBars: (dark) => StatusBar.setStyle({ style: dark ? Style.Dark : Style.Light }),
  };
}
