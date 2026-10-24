import { App } from "@capacitor/app";
import { Camera } from "@capacitor/camera";
import { Capacitor, registerPlugin } from "@capacitor/core";
import { Haptics, ImpactStyle, NotificationType } from "@capacitor/haptics";
import { SplashScreen } from "@capacitor/splash-screen";
import { StatusBar, Style } from "@capacitor/status-bar";

import type { Device, FeltMoment, PhotoTaken } from "./device";

// The camera library's codes for "no access" and "put away without a photo".
const CAMERA_DENIED = "OS-PLUG-CAMR-0003";
const CAMERA_CANCELLED = "OS-PLUG-CAMR-0006";

/** The iOS app's own plugin (App/SharedInbox.swift): what the share extension left. */
const SharedInbox = registerPlugin<{
  take(): Promise<{ files: { path: string; name: string }[] }>;
}>("SharedInbox");

const TYPES: Record<string, string> = {
  pdf: "application/pdf",
  png: "image/png",
  heic: "image/heic",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
};

/** Whatever was shared to the app since it last looked, as files to upload. */
async function takeShared(): Promise<File[]> {
  const { files } = await SharedInbox.take();
  return Promise.all(
    files.map(async ({ path, name }) => {
      const blob = await (await fetch(path)).blob();
      const type = TYPES[name.split(".").pop()?.toLowerCase() ?? ""] ?? "image/jpeg";
      return new File([blob], name, { type });
    }),
  );
}

let selecting: Promise<void> | null = null;

/**
 * The system's own feedback for each moment, as native apps use it: saved and failed are
 * the success and error notifications, a choice is the selection tick, a receipt read a
 * light tap on the way.
 */
function feel(moment: FeltMoment): Promise<void> {
  switch (moment) {
    case "saved":
      return Haptics.notification({ type: NotificationType.Success });
    case "failed":
      return Haptics.notification({ type: NotificationType.Error });
    case "selected":
      // iOS ticks only with a selection generator already prepared; one serves them all.
      selecting ??= Haptics.selectionStart();
      return selecting.then(() => Haptics.selectionChanged());
    case "read":
      return Haptics.impact({ style: ImpactStyle.Light });
  }
}

/**
 * A receipt photo from the app's own camera (F25.2.3). Access is asked for before the
 * viewfinder opens: the web view's file input opened its camera first on the first run
 * and the system's question never showed until the app was started again.
 */
async function takePhoto(): Promise<PhotoTaken> {
  const access = await Camera.requestPermissions({ permissions: ["camera"] });
  if (access.camera === "denied") return "denied";
  try {
    const photo = await Camera.takePhoto({ quality: 90, correctOrientation: true });
    if (!photo.webPath) return "cancelled";
    const blob = await (await fetch(photo.webPath)).blob();
    // The camera always saves a JPEG; the file URL does not say so reliably.
    return new File([blob], `receipt-${String(Date.now())}.jpg`, { type: "image/jpeg" });
  } catch (error) {
    const code = (error as { code?: unknown }).code;
    if (code === CAMERA_CANCELLED) return "cancelled";
    if (code === CAMERA_DENIED) return "denied";
    throw error;
  }
}

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
    feel,
    takePhoto,
    onShared(receive) {
      // Only the iOS app has a share extension yet; Android's share intent is not built.
      if (kind !== "ios") return () => undefined;
      const look = () => {
        void takeShared().then((files) => {
          if (files.length > 0) receive(files);
        });
      };
      look();
      const listener = App.addListener("appStateChange", ({ isActive }) => {
        if (isActive) look();
      });
      return () => {
        void listener.then((l) => l.remove());
      };
    },
  };
}
