import type { Device } from "./device";

/** The website: the browser owns its bars, back button and loading. */
export const webDevice: Device = {
  kind: "web",
  isApp: false,
  ready: () => Promise.resolve(),
  onBack: () => () => undefined,
  setDarkBars: () => Promise.resolve(),
  feel: () => Promise.resolve(),
};
