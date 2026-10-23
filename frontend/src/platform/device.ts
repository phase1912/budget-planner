/** Where the client runs: the website, or a store app on Android or iOS (E22, E25). */
export type DeviceKind = "web" | "android" | "ios";

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
  /** A short vibration for something done: a receipt read, a receipt saved. */
  feel(moment: "read" | "saved"): Promise<void>;
}
