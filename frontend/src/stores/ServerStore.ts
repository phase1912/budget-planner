import { makeAutoObservable } from "mobx";

import { onSlowReads, wakeServer } from "@/api/coldStart";

/**
 * Whether the server is still starting (cold start, F0.9): reads waiting unusually long
 * say so, and the shell tells the user instead of leaving them before a spinner.
 */
export class ServerStore {
  isWaking = false;

  constructor(subscribe: typeof onSlowReads = onSlowReads) {
    makeAutoObservable(this, {}, { autoBind: true });
    subscribe((waking) => {
      this.setWaking(waking);
    });
  }

  setWaking(waking: boolean): void {
    this.isWaking = waking;
  }

  /** Wake the server ahead of need, e.g. while the sign-in form is being filled in. */
  wake(): void {
    wakeServer();
  }
}
