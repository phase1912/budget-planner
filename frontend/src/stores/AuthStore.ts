import { makeAutoObservable, runInAction } from "mobx";
import type { Middleware } from "openapi-fetch";

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
  refreshToken: string | null = null;
  readonly authState = new AsyncState();
  private readonly api: ApiClient;
  private refreshPromise: Promise<boolean> | null = null;

  constructor(api: ApiClient = apiClient) {
    this.api = api;
    makeAutoObservable(this);

    // Hydrate state from localStorage on boot
    const savedToken = localStorage.getItem("budget_access_token");
    const savedRefreshToken = localStorage.getItem("budget_refresh_token");
    const savedUser = localStorage.getItem("budget_user");

    if (savedToken) {
      this.token = savedToken;
    }
    if (savedRefreshToken) {
      this.refreshToken = savedRefreshToken;
    }
    if (savedUser) {
      try {
        this.user = JSON.parse(savedUser) as User;
      } catch {
        console.error("Failed to parse user from local storage");
      }
    }

    this.setupInterceptor();
  }

  get isAuthenticated(): boolean {
    return this.token !== null;
  }

  private setupInterceptor() {
    const authMiddleware: Middleware = {
      onRequest: ({ request }) => {
        // Skip adding token to login/register routes
        if (
          !request.url.includes("/auth/login") &&
          !request.url.includes("/auth/register") &&
          !request.url.includes("/auth/refresh")
        ) {
          const currentToken = this.token;
          if (currentToken) {
            request.headers.set("Authorization", `Bearer ${currentToken}`);
          }
        }
        return request;
      },
      onResponse: async ({ request, response }) => {
        if (
          response.status === 401 &&
          !request.url.includes("/auth/login") &&
          !request.url.includes("/auth/refresh") &&
          this.refreshToken
        ) {
          const success = await this.refresh();
          if (success) {
            const newRequest = new Request(request);
            const currentToken = this.token;
            if (currentToken) {
              newRequest.headers.set("Authorization", `Bearer ${currentToken}`);
            }
            return await fetch(newRequest);
          } else {
            this.logoutLocally();
            window.location.href = "/login"; // Redirect on refresh fail
          }
        }
        return response;
      },
    };

    // Appending middleware is safe even if the client already has others.
    this.api.use(authMiddleware);
  }

  private persistSession(user: User, accessToken: string, refreshToken: string) {
    this.user = user;
    this.token = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem("budget_access_token", accessToken);
    localStorage.setItem("budget_refresh_token", refreshToken);
    localStorage.setItem("budget_user", JSON.stringify(user));
  }

  async refresh(): Promise<boolean> {
    const rToken = this.refreshToken;
    if (!rToken) return false;

    if (this.refreshPromise) return this.refreshPromise;

    this.refreshPromise = (async () => {
      try {
        const { data, error } = await this.api.POST("/auth/refresh", {
          body: { refresh_token: rToken },
        });

        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (error || !data) {
          return false;
        }

        runInAction(() => {
          this.persistSession(data.user, data.access_token, data.refresh_token);
        });
        return true;
      } catch {
        return false;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  async login(request: components["schemas"]["LoginRequest"]): Promise<boolean> {
    this.authState.start();
    try {
      const { data, error } = await this.api.POST("/auth/login", {
        body: request,
      });

      if (error || !data) {
        const detail = (error as ProblemDetail | undefined)?.detail;
        const msg = typeof detail === "string" ? detail : "Authentication failed";
        this.authState.fail(msg);
        return false;
      }

      this.persistSession(data.user, data.access_token, data.refresh_token);
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

      // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
      if (error || !data) {
        const detail = (error as ProblemDetail | undefined)?.detail;
        const msg = typeof detail === "string" ? detail : "Registration failed";
        this.authState.fail(msg);
        return false;
      }

      this.persistSession(data.user, data.access_token, data.refresh_token);
      this.authState.succeed();
      return true;
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      this.authState.fail(errMsg);
      return false;
    }
  }

  async logout(): Promise<void> {
    const rToken = this.refreshToken;
    if (rToken) {
      try {
        await this.api.POST("/auth/logout", {
          body: { refresh_token: rToken },
        });
      } catch {
        // Ignore network errors on logout
      }
    }
    this.logoutLocally();
  }

  logoutLocally(): void {
    this.user = null;
    this.token = null;
    this.refreshToken = null;
    localStorage.removeItem("budget_access_token");
    localStorage.removeItem("budget_refresh_token");
    localStorage.removeItem("budget_user");
    this.authState.reset();
  }
}
