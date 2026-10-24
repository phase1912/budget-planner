import { beforeEach, describe, expect, it, vi } from "vitest";

const plugins = vi.hoisted(() => ({
  back: undefined as ((event: { canGoBack: boolean }) => void) | undefined,
  exitApp: vi.fn(),
  hide: vi.fn(() => Promise.resolve()),
  setStyle: vi.fn(() => Promise.resolve()),
  notification: vi.fn(() => Promise.resolve()),
  impact: vi.fn(() => Promise.resolve()),
  selectionStart: vi.fn(() => Promise.resolve()),
  selectionChanged: vi.fn(() => Promise.resolve()),
  requestPermissions: vi.fn(() => Promise.resolve({ camera: "granted" })),
  takePhoto: vi.fn(() =>
    Promise.resolve({ webPath: "capacitor://localhost/_capacitor_file_/p.jpg" }),
  ),
  take: vi.fn(() =>
    Promise.resolve({
      files: [{ path: "capacitor://localhost/_capacitor_file_/s.pdf", name: "s.pdf" }],
    }),
  ),
  active: undefined as ((state: { isActive: boolean }) => void) | undefined,
}));

vi.mock("@capacitor/core", () => ({
  Capacitor: { getPlatform: () => "ios" },
  registerPlugin: () => ({ take: plugins.take }),
}));
vi.mock("@capacitor/app", () => ({
  App: {
    addListener: (
      name: string,
      handler: (event: { canGoBack: boolean; isActive: boolean }) => void,
    ) => {
      if (name === "appStateChange") plugins.active = handler as typeof plugins.active;
      else plugins.back = handler as typeof plugins.back;
      return Promise.resolve({ remove: vi.fn() });
    },
    exitApp: plugins.exitApp,
  },
}));
vi.mock("@capacitor/haptics", () => ({
  Haptics: {
    notification: plugins.notification,
    impact: plugins.impact,
    selectionStart: plugins.selectionStart,
    selectionChanged: plugins.selectionChanged,
  },
  ImpactStyle: { Light: "LIGHT" },
  NotificationType: { Success: "SUCCESS", Error: "ERROR" },
}));
vi.mock("@capacitor/camera", () => ({
  Camera: { requestPermissions: plugins.requestPermissions, takePhoto: plugins.takePhoto },
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

  it("in a store app, taps lightly when a receipt is read and confirms when it is saved", async () => {
    const device = nativeDevice();

    await device.feel("read");
    await device.feel("saved");
    await webDevice.feel("saved");

    expect(plugins.impact).toHaveBeenCalledWith({ style: "LIGHT" });
    expect(plugins.notification).toHaveBeenCalledWith({ type: "SUCCESS" });
    expect(plugins.notification).toHaveBeenCalledTimes(1);
  });

  it("in a store app, buzzes a failure and ticks each changed choice from one generator", async () => {
    const device = nativeDevice();

    await device.feel("failed");
    await device.feel("selected");
    await device.feel("selected");

    expect(plugins.notification).toHaveBeenCalledWith({ type: "ERROR" });
    expect(plugins.selectionChanged).toHaveBeenCalledTimes(2);
    expect(plugins.selectionStart.mock.invocationCallOrder[0]).toBeLessThan(
      plugins.selectionChanged.mock.invocationCallOrder[0] ?? 0,
    );
  });

  it("in a store app, asks for the camera before opening it and hands back the photo", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(new Blob(["jpeg"], { type: "image/jpeg" })))),
    );
    const photo = await nativeDevice().takePhoto?.();

    expect(plugins.requestPermissions).toHaveBeenCalledWith({ permissions: ["camera"] });
    expect(plugins.requestPermissions.mock.invocationCallOrder[0]).toBeLessThan(
      plugins.takePhoto.mock.invocationCallOrder[0] ?? 0,
    );
    expect(photo).toBeInstanceOf(File);
    expect((photo as File).type).toBe("image/jpeg");
    expect(webDevice.takePhoto).toBeNull();
    vi.unstubAllGlobals();
  });

  it("in a store app, says so when the camera is refused, and opens nothing", async () => {
    plugins.requestPermissions.mockResolvedValueOnce({ camera: "denied" });

    expect(await nativeDevice().takePhoto?.()).toBe("denied");
    expect(plugins.takePhoto).not.toHaveBeenCalled();
  });

  it("in a store app, takes the camera put away as no photo, not an error", async () => {
    plugins.takePhoto.mockRejectedValueOnce(
      Object.assign(new Error("x"), { code: "OS-PLUG-CAMR-0006" }),
    );

    expect(await nativeDevice().takePhoto?.()).toBe("cancelled");
  });

  it("in the iOS app, hands over receipts shared to it at start and on coming back", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(new Blob(["%PDF"])))),
    );
    const receive = vi.fn();

    nativeDevice().onShared(receive);
    await vi.waitFor(() => {
      expect(receive).toHaveBeenCalledTimes(1);
    });
    plugins.active?.({ isActive: true });
    await vi.waitFor(() => {
      expect(receive).toHaveBeenCalledTimes(2);
    });

    const [files] = receive.mock.calls[0] as [File[]];
    expect(files.map((f) => [f.name, f.type])).toEqual([["s.pdf", "application/pdf"]]);
    vi.unstubAllGlobals();
  });
});
