import { describe, expect, it, vi } from "vitest";

import { InstallStore } from "./InstallStore";

function browser(userAgent: string, standalone = false): Window {
  const listeners: Record<string, (event: Event) => void> = {};
  return {
    navigator: { userAgent, standalone } as unknown as Navigator,
    matchMedia: () => ({ matches: standalone }) as MediaQueryList,
    addEventListener: (type: string, listener: (event: Event) => void) => {
      listeners[type] = listener;
    },
    fire: (type: string, event: Event) => {
      listeners[type]?.(event);
    },
  } as unknown as Window;
}

const IPHONE_SAFARI =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1";
const ANDROID_CHROME =
  "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36";

describe("InstallStore", () => {
  it("explains the Share-menu step on iPhone Safari, which offers no install dialog", () => {
    const store = new InstallStore(browser(IPHONE_SAFARI));
    expect(store.showsIosHint).toBe(true);
    expect(store.offersInstall).toBe(false);
  });

  it("offers nothing once the app runs from the home screen", () => {
    const store = new InstallStore(browser(IPHONE_SAFARI, true));
    expect(store.showsIosHint).toBe(false);
  });

  it("replays Chrome's install dialog on request, and stops offering once accepted", async () => {
    const win = browser(ANDROID_CHROME);
    const store = new InstallStore(win);
    const prompt = vi.fn().mockResolvedValue(undefined);
    const event = Object.assign(new Event("beforeinstallprompt"), {
      prompt,
      userChoice: Promise.resolve({ outcome: "accepted" as const }),
    });
    (win as unknown as { fire: (t: string, e: Event) => void }).fire("beforeinstallprompt", event);
    expect(store.offersInstall).toBe(true);

    await store.install();

    expect(prompt).toHaveBeenCalled();
    expect(store.offersInstall).toBe(false);
  });

  it("remembers that the hint was dismissed", () => {
    new InstallStore(browser(IPHONE_SAFARI)).dismiss();
    expect(new InstallStore(browser(IPHONE_SAFARI)).showsIosHint).toBe(false);
    localStorage.clear();
  });
});
