import { makeAutoObservable } from "mobx";

import { device } from "@/platform";

export type ToastType = "error" | "success" | "info";

/** Where a message offers to go next — e.g. the month a receipt was stored in. */
export interface ToastLink {
  to: string;
  label: string;
}

export interface ToastMessage {
  message: string;
  type: ToastType;
  link?: ToastLink;
}

/**
 * The one short message on screen. Every saved or failed action passes through here, so
 * the store apps' vibration for success and failure is given here too (F25.2.3).
 */
export class ToastStore {
  toast: ToastMessage | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  showError(message: string) {
    this.toast = { message, type: "error" };
    void device.feel("failed");
  }

  showSuccess(message: string, link?: ToastLink) {
    this.toast = link ? { message, type: "success", link } : { message, type: "success" };
    void device.feel("saved");
  }

  showInfo(message: string) {
    this.toast = { message, type: "info" };
  }

  clearToast() {
    this.toast = null;
  }
}
