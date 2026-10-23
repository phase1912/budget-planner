import { beforeEach, describe, expect, it, vi } from "vitest";

const plugins = vi.hoisted(() => ({
  back: undefined as ((event: { canGoBack: boolean }) => void) | undefined,
  exitApp: vi.fn(),
  hide: vi.fn(() => Promise.resolve()),
  setStyle: vi.fn(() => Promise.resolve()),
}));

vi.mock("@capacitor/core", () => ({ Capacitor: { getPlatform: () => "ios" } }));
vi.mock("@capacitor/app", () => ({
  App: {
    addListener: (_name: string, handler: (event: { canGoBack: boolean }) => void) => {
      plugins.back = handler;
      return Promise.resolve({ remove: vi.fn() });
    },
    exitApp: plugins.exitApp,
  },
}));
vi.mock("@capacitor/splash-screen", () => ({ SplashScreen: { hide: plugins.hide } }));
vi.mock("@capacitor/status-bar", () => ({
  StatusBar: { setStyle: plugins.setStyle },
  Style: { Dark: "DARK", Light: "LIGHT" },
}));

import { nativeDevice } from "./nativeDevice";
import { webDevice } from "./webDevice";

describe("the device the client runs on (F22.2.1, F25.2.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("is the website as it always was: no bars, no back button, nothing to hide", async () => {
    const goBack = vi.fn();
    webDevice.onBack(goBack)();
    await webDevice.ready();
    await webDevice.setDarkBars(true);

    expect([webDevice.kind, webDevice.isApp]).toEqual(["web", false]);
    expect(goBack).not.toHaveBeenCalled();
  });

  it("in a store app, goes back a screen, and leaves the app from the first", () => {
    const device = nativeDevice();
    const goBack = vi.fn();
    device.onBack(goBack);

    plugins.back?.({ canGoBack: true });
    plugins.back?.({ canGoBack: false });

    expect([device.kind, device.isApp]).toEqual(["ios", true]);
    expect(goBack).toHaveBeenCalledTimes(1);
    expect(plugins.exitApp).toHaveBeenCalledTimes(1);
  });

  it("in a store app, hides the launch screen once ready and lights the bars for a dark ground", async () => {
    const device = nativeDevice();

    await device.ready();
    await device.setDarkBars(true);
    await device.setDarkBars(false);

    expect(plugins.hide).toHaveBeenCalled();
    expect(plugins.setStyle.mock.calls).toEqual([[{ style: "DARK" }], [{ style: "LIGHT" }]]);
  });
});
