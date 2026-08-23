import { makeAutoObservable } from "mobx";

import { apiClient, type ApiClient } from "@/api/client";
import type { components } from "@/api/schema";
import { AsyncState } from "@/stores/AsyncState";

export type User = components["schemas"]["UserResponse"];

interface ProblemDetail {
  detail?: string | unknown[];
}

export class AuthStore {
  user: User | null = null;
  token: string | null = null;
  readonly authState = new AsyncState();
  private readonly api: ApiClient;

  constructor(api: ApiClient = apiClient) {
    this.api = api;
    makeAutoObservable(this);
    
    // Hydrate state from localStorage on boot
    const savedToken = localStorage.getItem("budget_access_token");
    const savedUser = localStorage.getItem("budget_user");
    
    if (savedToken) {
      this.token = savedToken;
    }
    if (savedUser) {
      try {
        this.user = JSON.parse(savedUser) as User;
      } catch (e) {
        console.error("Failed to parse user from local storage", e);
      }
    }
  }

  get isAuthenticated(): boolean {
    return this.token !== null;
  }

  async login(request: components["schemas"]["LoginRequest"]): Promise<boolean> {
    this.authState.start();
    try {
      const { data, error } = await this.api.POST("/auth/login", {
        body: request,
      });

      if (error) {
        const detail = (error as ProblemDetail).detail;
        const msg = typeof detail === "string" ? detail : "Authentication failed";
        this.authState.fail(msg);
        return false;
      }

      this.user = data.user;
      this.token = data.access_token;
      localStorage.setItem("budget_access_token", data.access_token);
      localStorage.setItem("budget_user", JSON.stringify(data.user));
      this.authState.succeed();
      return true;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      this.authState.fail(errMsg);
      return false;
    }
  }

  async register(request: components["schemas"]["RegisterRequest"]): Promise<boolean> {
    this.authState.start();
    try {
      const { data, error } = await this.api.POST("/auth/register", {
        body: request,
      });

      if (error) {
        const detail = (error as ProblemDetail).detail;
        const msg = typeof detail === "string" ? detail : "Registration failed";
        this.authState.fail(msg);
        return false;
      }

      this.user = data.user;
      this.token = data.access_token;
      localStorage.setItem("budget_access_token", data.access_token);
      localStorage.setItem("budget_user", JSON.stringify(data.user));
      this.authState.succeed();
      return true;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      this.authState.fail(errMsg);
      return false;
    }
  }

  logout(): void {
    this.user = null;
    this.token = null;
    localStorage.removeItem("budget_access_token");
    this.authState.reset();
  }
}
