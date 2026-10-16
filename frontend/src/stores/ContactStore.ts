import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { screenLanguage } from "@/i18n/languages";
import { AsyncState } from "@/stores/AsyncState";

export type ContactTopic = components["schemas"]["ContactTopic"];

/**
 * Writing to the people running the service from the Help page (F17.10.2). The message is
 * mailed to the administrators with the sender to reply to; the sender gets a copy.
 */
export class ContactStore {
  readonly state = new AsyncState();
  private readonly api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
    makeAutoObservable<this, "api">(this, { api: false }, { autoBind: true });
  }

  /** Send the message; `website` is the hidden trap field a person leaves empty. */
  async send(email: string, topic: ContactTopic, message: string, website = ""): Promise<void> {
    this.state.start();
    const response = await settle(() =>
      this.api.POST("/api/v1/contact", {
        body: { email, topic, message, website, language: screenLanguage(i18n.language) },
      }),
    );
    runInAction(() => {
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:account.failed")));
        return;
      }
      this.state.succeed();
    });
  }

  /** Start a new message after one was sent. */
  reset(): void {
    this.state.reset();
  }
}
