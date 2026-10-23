import { reaction } from "mobx";

import { ThemeStore } from "@/stores/ThemeStore";
import { AuthStore } from "@/stores/AuthStore";
import { ToastStore } from "@/stores/ToastStore";
import { ProfileStore } from "@/stores/ProfileStore";
import { UploadStore } from "@/stores/UploadStore";
import { apiClient } from "@/api/client";

import { CategoriesStore } from "@/stores/CategoriesStore";
import { ReceiptStore } from "@/stores/ReceiptStore";
import { BudgetStore } from "@/stores/BudgetStore";
import { StatisticsStore } from "@/stores/StatisticsStore";
import { ExportStore } from "@/stores/ExportStore";
import { GoalsStore } from "@/stores/GoalsStore";
import { AdviceStore } from "@/stores/AdviceStore";
import { QuotaStore } from "@/stores/QuotaStore";
import { AccuracyStore } from "@/stores/AccuracyStore";
import { ProductsStore } from "@/stores/ProductsStore";
import { ExplorationStore } from "@/stores/ExplorationStore";
import { TripsStore } from "@/stores/TripsStore";
import { InstallStore } from "@/stores/InstallStore";
import { HouseholdStore } from "@/stores/HouseholdStore";
import { LanguageStore } from "@/stores/LanguageStore";
import { ServerStore } from "@/stores/ServerStore";
import { AccountStore } from "@/stores/AccountStore";
import { ContactStore } from "@/stores/ContactStore";
import { AnalyticsStore } from "@/stores/AnalyticsStore";
import { AdminStore } from "@/stores/AdminStore";
import { TwoFactorStore } from "@/stores/TwoFactorStore";
import { IncomeStore } from "@/stores/IncomeStore";
import { BankAccountsStore } from "@/stores/BankAccountsStore";
import { AssistantStore } from "@/stores/AssistantStore";

/**
 * Single instantiation point for every MobX store in the client (F9.2.1). Feature
 * epics add their store as a field here; a component or another store never imports
 * a store directly — it reaches every store through this composition, injected via
 * `useStores()`.
 */
export class RootStore {
  readonly themeStore: ThemeStore;
  readonly authStore: AuthStore;
  readonly toastStore: ToastStore;
  readonly profileStore: ProfileStore;
  readonly uploadStore: UploadStore;
  readonly receiptStore: ReceiptStore;
  readonly categoriesStore: CategoriesStore;
  readonly budgetStore: BudgetStore;
  readonly statisticsStore: StatisticsStore;
  readonly exportStore: ExportStore;
  readonly goalsStore: GoalsStore;
  readonly adviceStore: AdviceStore;
  readonly quotaStore: QuotaStore;
  readonly accuracyStore: AccuracyStore;
  readonly productsStore: ProductsStore;
  readonly explorationStore: ExplorationStore;
  readonly tripsStore: TripsStore;
  readonly installStore: InstallStore;
  readonly householdStore: HouseholdStore;
  readonly languageStore: LanguageStore;
  readonly serverStore: ServerStore;
  readonly accountStore: AccountStore;
  readonly contactStore: ContactStore;
  readonly analyticsStore: AnalyticsStore;
  readonly adminStore: AdminStore;
  readonly twoFactorStore: TwoFactorStore;
  readonly incomeStore: IncomeStore;
  readonly bankAccountsStore: BankAccountsStore;
  readonly assistantStore: AssistantStore;

  constructor() {
    this.themeStore = new ThemeStore();
    this.serverStore = new ServerStore();
    this.toastStore = new ToastStore();
    this.authStore = new AuthStore(apiClient);
    this.languageStore = new LanguageStore(this.authStore);
    this.profileStore = new ProfileStore(
      apiClient,
      this.authStore,
      this.toastStore,
      this.themeStore,
    );
    this.accountStore = new AccountStore(apiClient, this.authStore, this.toastStore);
    this.contactStore = new ContactStore(apiClient);
    this.analyticsStore = new AnalyticsStore(apiClient);
    this.adminStore = new AdminStore(apiClient, this.toastStore);
    this.twoFactorStore = new TwoFactorStore(apiClient, this.authStore, this.toastStore);
    this.incomeStore = new IncomeStore(apiClient, this.toastStore);
    this.bankAccountsStore = new BankAccountsStore(apiClient, this.toastStore);
    // A card the assistant saved changed the month, or a setting: Home and Plan read it
    // again, and the profile too, so a new language or palette shows at once (F21.11).
    this.assistantStore = new AssistantStore(apiClient, this.toastStore, () => {
      void this.budgetStore.refresh();
      void this.profileStore.loadProfile();
    });
    this.budgetStore = new BudgetStore();
    // Any receipt change may have recalculated the month on screen (BRD D6, F6.5).
    const refreshMonth = () => void this.budgetStore.refresh();
    this.quotaStore = new QuotaStore();
    this.accuracyStore = new AccuracyStore();
    this.productsStore = new ProductsStore(this.toastStore);
    this.explorationStore = new ExplorationStore(this.toastStore);
    this.tripsStore = new TripsStore(this.toastStore, refreshMonth);
    this.installStore = new InstallStore();
    this.householdStore = new HouseholdStore(this.toastStore);
    // Every upload started uses up receipt reads (F10.6), whether or not it is stored.
    this.uploadStore = new UploadStore(apiClient, this.toastStore, refreshMonth, () => {
      void this.quotaStore.load();
    });
    this.uploadStore.useTrips(() => this.tripsStore.trips);
    this.receiptStore = new ReceiptStore(this.toastStore, refreshMonth);
    this.categoriesStore = new CategoriesStore();
    this.statisticsStore = new StatisticsStore();
    this.exportStore = new ExportStore(this.toastStore);
    this.adviceStore = new AdviceStore();
    // A goal's new target changes where its month is heading (F8.7): ask again.
    this.goalsStore = new GoalsStore(this.toastStore, () => void this.adviceStore.loadProgress());
    // The month view remembers where it was left; a new account starts afresh,
    // and never sees the previous one's figures while its own load.
    // Signing in brings the account's language with it (F9.9).
    reaction(
      () => `${this.authStore.user?.id ?? ""}:${this.authStore.user?.language ?? ""}`,
      () => {
        const user = this.authStore.user;
        if (user) this.languageStore.adoptAccount(user.language);
      },
      // Keyed by value: the user object is replaced on every profile load, its language is not.
      { fireImmediately: true },
    );
    // The account's look follows it to every device (F23.1).
    reaction(
      () => `${this.authStore.user?.palette ?? ""}:${String(this.authStore.user?.dark_at_night)}`,
      () => {
        const user = this.authStore.user;
        if (user) this.themeStore.adoptAccount(user.palette, user.dark_at_night);
      },
      { fireImmediately: true },
    );
    reaction(
      () => this.authStore.user?.id,
      () => {
        this.budgetStore.reset();
        this.statisticsStore.reset();
        this.goalsStore.reset();
        this.adviceStore.reset();
        this.quotaStore.reset();
        this.accuracyStore.reset();
        this.productsStore.reset();
        this.explorationStore.reset();
        this.tripsStore.reset();
        this.bankAccountsStore.reset();
        this.assistantStore.reset();
        this.householdStore.reset();
        this.receiptStore.resetScope();
        this.adminStore.reset();
        this.incomeStore.reset();
        this.twoFactorStore.close();
      },
    );
  }
}
