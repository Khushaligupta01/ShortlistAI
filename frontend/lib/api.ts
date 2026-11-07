import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from "./auth";
import type { ApiError, CurrentUser, RequisitionListResponse, TokenResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiClient {
  private async request<T>(
    path: string,
    options: RequestInit = {},
    retry = true
  ): Promise<T> {
    const token = getAccessToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> ?? {}),
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    // Token expired — attempt refresh once
    if (response.status === 401 && retry) {
      const refreshed = await this.tryRefresh();
      if (refreshed) {
        return this.request<T>(path, options, false);
      }
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }

    if (!response.ok) {
      let errorData: ApiError;
      try {
        errorData = await response.json();
      } catch {
        throw new Error(`HTTP ${response.status}`);
      }
      throw new Error(errorData.message ?? `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  private async tryRefresh(): Promise<boolean> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    try {
      const resp = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!resp.ok) return false;
      const tokens: TokenResponse = await resp.json();
      saveTokens(tokens);
      return true;
    } catch {
      return false;
    }
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const resp = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ message: "Login failed" }));
      throw new Error(err.message ?? err.detail ?? "Login failed");
    }
    return resp.json();
  }

  async logout(refreshToken: string): Promise<void> {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken() ?? ""}`,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async getCurrentUser(): Promise<CurrentUser> {
    return this.request<CurrentUser>("/api/v1/auth/me");
  }

  async getRequisitions(page = 1, pageSize = 20): Promise<RequisitionListResponse> {
    return this.request<RequisitionListResponse>(
      `/api/v1/requisitions?page=${page}&page_size=${pageSize}`
    );
  }
}

export const api = new ApiClient();
