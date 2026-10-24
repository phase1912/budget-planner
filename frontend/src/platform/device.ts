/** Where the client runs: the website, or a store app on Android or iOS (E22, E25). */
export type DeviceKind = "web" | "android" | "ios";

/** The moments the phone answers with a vibration. */
export type FeltMoment = "read" | "saved" | "failed" | "selected";

/** What the app's own camera gave back: the photo, nothing (put away), or no access. */
export type PhotoTaken = File | "cancelled" | "denied";

/**
 * Everything that differs between the website and the store apps, asked in one place so
 * no screen ever asks "am I in the app" (F22.2.1, F25.2.1). The web answers are the
 * site's behaviour today; the native ones come from Capacitor's plugins.
 */
export interface Device {
  readonly kind: DeviceKind;
  /** Whether this is a store app rather than the website. */
  readonly isApp: boolean;
  /** The first screen is drawn: the launch screen may go. */
  ready(): Promise<void>;
  /** Android's back button and gesture: go back a screen, or leave the app at the first. */
  onBack(goBack: () => void): () => void;
  /** Light or dark status and navigation bars, following the palette's ground. */
  setDarkBars(dark: boolean): Promise<void>;
  /**
   * A short vibration where a native app gives one (F25.2.3): something saved, something
   * failed, a receipt read, a choice changed (a tab, a segment, a switch, a chart's day).
   */
  feel(moment: FeltMoment): Promise<void>;
  /**
   * The phone's camera, asked for access first so the system's question always comes
   * before the viewfinder (F25.2.3). Null on the website, where the browser's own file
   * input opens the camera.
   */
  readonly takePhoto: (() => Promise<PhotoTaken>) | null;
  /**
   * Receipts shared to the app from another one ("Share → Budget Agent", F25.2.2), handed
   * over at start and each time the app comes back to the front. Returns the unsubscribe.
   */
  onShared(receive: (files: File[]) => void): () => void;
}
