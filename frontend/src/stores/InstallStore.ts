import { makeAutoObservable } from "mobx";

/** The event Chrome fires when it is willing to install the app (not in TS's DOM types). */
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISSED_KEY = "budget_install_hint_dismissed";

function readDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Whether and how this browser can install the app on the home screen (BRD — F9.8.3).
 *
 * Chrome on Android offers installing through an event we keep and replay on request;
 * Safari on iPhone never does, so there the app can only explain the Share-menu step.
 * Nothing is offered once the app runs installed, or after the hint was dismissed.
 */
export class InstallStore {
  private promptEvent: InstallPromptEvent | null = null;
  canPrompt = false;
  installed: boolean;
  isIosSafari: boolean;
  dismissed = readDismissed();

  constructor(win: Window = window) {
    const standalone =
      // jsdom and old browsers have no matchMedia; there the app is simply not installed.
      (typeof win.matchMedia === "function" &&
        win.matchMedia("(display-mode: standalone)").matches) ||
      (win.navigator as Navigator & { standalone?: boolean }).standalone === true;
    this.installed = standalone;
    const ua = win.navigator.userAgent;
    this.isIosSafari = /iPhone|iPad|iPod/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
    makeAutoObservable<this, "promptEvent">(this, { promptEvent: false }, { autoBind: true });
    win.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      this.capture(event as InstallPromptEvent);
    });
    win.addEventListener("appinstalled", () => {
      this.markInstalled();
    });
  }

  /** Whether to show the iPhone "Add to Home Screen" hint. */
  get showsIosHint(): boolean {
    return this.isIosSafari && !this.installed && !this.dismissed;
  }

  /** Whether to offer the browser's own install dialog. */
  get offersInstall(): boolean {
    return this.canPrompt && !this.installed;
  }

  capture(event: InstallPromptEvent): void {
    this.promptEvent = event;
    this.canPrompt = true;
  }

  markInstalled(): void {
    this.installed = true;
    this.canPrompt = false;
    this.promptEvent = null;
  }

  /** Open the browser's install dialog; a refusal leaves the offer for later. */
  async install(): Promise<void> {
    const event = this.promptEvent;
    if (!event) return;
    await event.prompt();
    const { outcome } = await event.userChoice;
    if (outcome === "accepted") this.markInstalled();
  }

  /** Hide the hint for good on this device. */
  dismiss(): void {
    this.dismissed = true;
    try {
      localStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // Private mode: the hint simply comes back next visit.
    }
  }
}
