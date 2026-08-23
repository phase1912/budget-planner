import { makeAutoObservable } from "mobx";

export type ToastType = "error" | "success" | "info";

export interface ToastMessage {
  message: string;
  type: ToastType;
}

export class ToastStore {
  toast: ToastMessage | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  showError(message: string) {
    this.toast = { message, type: "error" };
  }

  showSuccess(message: string) {
    this.toast = { message, type: "success" };
  }

  showInfo(message: string) {
    this.toast = { message, type: "info" };
  }

  clearToast() {
    this.toast = null;
  }
}
