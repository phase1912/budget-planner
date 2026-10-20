import { makeAutoObservable, runInAction } from "mobx";

import type { ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { errorMessage, settle } from "@/api/errors";
import i18n from "@/i18n";
import { AsyncState } from "@/stores/AsyncState";
import type { ToastStore } from "@/stores/ToastStore";

export type BankAccount = components["schemas"]["AccountRead"];
export type BankAccountRequest = components["schemas"]["AccountRequest"];
export type AccountKind = BankAccount["kind"];
export type AccountHistory = components["schemas"]["HistoryRead"];
export type AccountEntry = components["schemas"]["EntryRead"];
export type TransferRule = components["schemas"]["TransferRuleRead"];
export type TransferRuleRequest = components["schemas"]["TransferRuleRequest"];
export type ExpectedIncome = components["schemas"]["ExpectedRead"];

/**
 * The card a user's sums land on when no other account is picked (F23.15): their own
 * purchase card, else the family's shared one — as the server decides it.
 */
export function purchaseCardId(accounts: readonly BankAccount[]): string | undefined {
  const own = accounts.find((a) => a.for_purchases && !a.shared && a.mine);
  return (own ?? accounts.find((a) => a.for_purchases && a.shared))?.id;
}

/**
 * Where the money is (F23.15): the accounts the user sees — their own and the family's
 * shared ones — with balances, one account's history month by month, the money moved
 * between them, monthly transfers, and "about" incomes waiting to be confirmed.
 */
export class BankAccountsStore {
  readonly state = new AsyncState();
  readonly saveState = new AsyncState();
  accounts: BankAccount[] = [];
  total = "0";
  setAside = "0";
  loaded = false;
  history: AccountHistory | null = null;
  readonly historyState = new AsyncState();
  transfers: TransferRule[] = [];
  expected: ExpectedIncome[] = [];
  private readonly api: ApiClient;
  private readonly toastStore: ToastStore;
  private historyRequest = 0;

  constructor(api: ApiClient, toastStore: ToastStore) {
    this.api = api;
    this.toastStore = toastStore;
    makeAutoObservable<this, "api" | "toastStore" | "historyRequest">(
      this,
      { api: false, toastStore: false, historyRequest: false },
      { autoBind: true },
    );
  }

  /** Whether the user keeps any account: without one, the balance works as before. */
  get any(): boolean {
    return this.accounts.length > 0;
  }

  /** The account with `id`, if the user sees it. */
  byId(id: string): BankAccount | undefined {
    return this.accounts.find((a) => a.id === id);
  }

  /** Every account with its balance on `today`, the user's own date. */
  async load(today: string): Promise<void> {
    this.state.start();
    const response = await settle(() =>
      this.api.GET("/api/v1/accounts", { params: { query: { today } } }),
    );
    runInAction(() => {
      this.loaded = true;
      if (response.error !== undefined) {
        this.state.fail(errorMessage(response.error, i18n.t("messages:accounts.loadFailed")));
        return;
      }
      this.accounts = response.data.accounts;
      this.total = response.data.total;
      this.setAside = response.data.set_aside;
      this.state.succeed();
    });
  }

  /** One account's history in `month` (YYYY-MM); only the latest request lands. */
  async loadHistory(id: string, month: string, today: string): Promise<void> {
    this.historyState.start();
    const request = ++this.historyRequest;
    const response = await settle(() =>
      this.api.GET("/api/v1/accounts/{account_id}/history", {
        params: { path: { account_id: id }, query: { month, today } },
      }),
    );
    runInAction(() => {
      if (request !== this.historyRequest) return;
      if (response.error !== undefined) {
        this.historyState.fail(
          errorMessage(response.error, i18n.t("messages:accounts.loadFailed")),
        );
        return;
      }
      this.history = response.data;
      this.historyState.succeed();
    });
  }

  /** The monthly transfers between accounts the user sees. */
  async loadTransfers(): Promise<void> {
    const response = await settle(() => this.api.GET("/api/v1/accounts/transfers"));
    runInAction(() => {
      if (response.error === undefined) this.transfers = response.data;
    });
  }

  /** "About" incomes whose day has come, waiting for what really came (F_Check). */
  async loadExpected(today: string): Promise<void> {
    const response = await settle(() =>
      this.api.GET("/api/v1/accounts/expected", { params: { query: { today } } }),
    );
    runInAction(() => {
      if (response.error === undefined) this.expected = response.data;
    });
  }

  /** Open an account. */
  open(body: BankAccountRequest, today: string): Promise<boolean> {
    return this.save(
      () => this.api.POST("/api/v1/accounts", { params: { query: { today } }, body }),
      today,
    );
  }

  /** Change an account's name, start, tax rate or whose it is. */
  change(id: string, body: BankAccountRequest, today: string): Promise<boolean> {
    return this.save(
      () =>
        this.api.PUT("/api/v1/accounts/{account_id}", {
          params: { path: { account_id: id }, query: { today } },
          body,
        }),
      today,
    );
  }

  /** Delete an account and the moves on it. */
  remove(id: string, today: string): Promise<boolean> {
    return this.save(
      () =>
        this.api.DELETE("/api/v1/accounts/{account_id}", {
          params: { path: { account_id: id } },
        }),
      today,
    );
  }

  /** Money reached an account: from outside, or from another own account (a transfer). */
  moneyIn(
    id: string,
    body: components["schemas"]["MoneyInRequest"],
    today: string,
  ): Promise<boolean> {
    return this.save(
      () =>
        this.api.POST("/api/v1/accounts/{account_id}/money-in", {
          params: { path: { account_id: id }, query: { today } },
          body,
        }),
      today,
    );
  }

  /** Move money between two accounts: neither income nor spending. */
  move(body: components["schemas"]["MoveRequest"], today: string): Promise<boolean> {
    return this.save(
      () => this.api.POST("/api/v1/accounts/moves", { params: { query: { today } }, body }),
      today,
    );
  }

  /** Correct a move of this month. */
  changeMove(id: string, amount: string, movedOn: string, today: string): Promise<boolean> {
    return this.save(
      () =>
        this.api.PUT("/api/v1/accounts/moves/{move_id}", {
          params: { path: { move_id: id }, query: { today } },
          body: { amount, moved_on: movedOn },
        }),
      today,
    );
  }

  /** Remove a move of this month. */
  deleteMove(id: string, today: string): Promise<boolean> {
    return this.save(
      () =>
        this.api.DELETE("/api/v1/accounts/moves/{move_id}", {
          params: { path: { move_id: id }, query: { today } },
        }),
      today,
    );
  }

  /** Correct an income on an account this month; its tax follows the account's rate. */
  changeIncome(id: string, amount: string, receivedOn: string, today: string): Promise<boolean> {
    return this.save(
      () =>
        this.api.PUT("/api/v1/accounts/incomes/{income_id}", {
          params: { path: { income_id: id }, query: { today } },
          body: { amount, received_on: receivedOn },
        }),
      today,
    );
  }

  /** Remove an income on an account this month. */
  removeIncome(id: string, today: string): Promise<boolean> {
    return this.save(
      () => this.api.DELETE("/api/v1/income/{income_id}", { params: { path: { income_id: id } } }),
      today,
    );
  }

  /** Bring an account to what the bank says now. */
  adjust(id: string, balance: string, today: string): Promise<boolean> {
    return this.save(
      () =>
        this.api.POST("/api/v1/accounts/{account_id}/adjust", {
          params: { path: { account_id: id }, query: { today } },
          body: { balance },
        }),
      today,
    );
  }

  /** Change this month's bill or transfer made by a rule; 0 skips it. */
  changeOccurrence(
    kind: "bill" | "transfer",
    ruleId: string,
    amount: string,
    today: string,
  ): Promise<boolean> {
    return this.save(
      () =>
        this.api.PUT("/api/v1/accounts/occurrences/{rule_id}", {
          params: { path: { rule_id: ruleId }, query: { today } },
          body: { kind, amount },
        }),
      today,
    );
  }

  /** Say what an "about" income really brought this month. */
  async confirm(sourceId: string, amount: string, today: string): Promise<boolean> {
    const ok = await this.save(
      () =>
        this.api.POST("/api/v1/accounts/expected/{source_id}/confirm", {
          params: { path: { source_id: sourceId }, query: { today } },
          body: { amount },
        }),
      today,
    );
    if (ok) await this.loadExpected(today);
    return ok;
  }

  /** Move money every month by itself. */
  async addTransfer(body: TransferRuleRequest, today: string): Promise<boolean> {
    const ok = await this.save(
      () => this.api.POST("/api/v1/accounts/transfers", { params: { query: { today } }, body }),
      today,
    );
    if (ok) await this.loadTransfers();
    return ok;
  }

  /** Change a monthly transfer from now on. */
  async changeTransfer(id: string, body: TransferRuleRequest, today: string): Promise<boolean> {
    const ok = await this.save(
      () =>
        this.api.PUT("/api/v1/accounts/transfers/{rule_id}", {
          params: { path: { rule_id: id } },
          body,
        }),
      today,
    );
    if (ok) await this.loadTransfers();
    return ok;
  }

  /** Stop a monthly transfer from next month. */
  async endTransfer(id: string, today: string): Promise<boolean> {
    const ok = await this.save(
      () =>
        this.api.DELETE("/api/v1/accounts/transfers/{rule_id}", {
          params: { path: { rule_id: id }, query: { today } },
        }),
      today,
    );
    if (ok) await this.loadTransfers();
    return ok;
  }

  reset(): void {
    this.accounts = [];
    this.total = "0";
    this.setAside = "0";
    this.loaded = false;
    this.history = null;
    this.transfers = [];
    this.expected = [];
    this.state.reset();
  }

  /** Send a change, then read the balances (and the open history) again. */
  private async save(send: () => Promise<{ error?: unknown }>, today: string): Promise<boolean> {
    this.saveState.start();
    const response = await settle(send);
    const ok = response.error === undefined;
    runInAction(() => {
      if (ok) {
        this.saveState.succeed();
        this.toastStore.showSuccess(i18n.t("messages:accounts.saved"));
      } else {
        const message = errorMessage(response.error, i18n.t("messages:accounts.failed"));
        this.saveState.fail(message);
        this.toastStore.showError(message);
      }
    });
    if (ok) {
      const open = this.history;
      await Promise.all([
        this.load(today),
        open ? this.loadHistory(open.account.id, open.month, today) : Promise.resolve(),
      ]);
    }
    return ok;
  }
}
