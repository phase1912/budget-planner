import { makeAutoObservable } from "mobx";

export type AsyncStatus = "idle" | "loading" | "success" | "error";

/**
 * Tracks the idle/loading/success/error lifecycle every async store action follows
 * (F9.2.2), so a reader recognises the pattern in any store without re-deriving it.
 * A store composes one of these per async action rather than hand-rolling its own
 * status flags.
 */
export class AsyncState {
  status: AsyncStatus = "idle";
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  get isLoading(): boolean {
    return this.status === "loading";
  }

  start(): void {
    this.status = "loading";
    this.error = null;
  }

  succeed(): void {
    this.status = "success";
    this.error = null;
  }

  fail(error: string): void {
    this.status = "error";
    this.error = error;
  }

  reset(): void {
    this.status = "idle";
    this.error = null;
  }
}
