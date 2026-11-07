import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from "./auth";
import type {
  ApiError,
  CurrentUser,
  JDExtractionResult,
  Requisition,
  RequisitionListResponse,
  ScorecardCreate,
  ScorecardResponse,
  ScorecardUpdate,
  TokenResponse,
} from "./types";

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
      ...((options.headers as Record<string, string>) ?? {}),
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
      throw new Error(
        errorData.message ?? errorData.detail ?? `HTTP ${response.status}`
      );
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

  // ── Requisitions ─────────────────────────────────────────────────────────

  async getRequisitions(
    page = 1,
    pageSize = 20,
    status?: string,
    search?: string
  ): Promise<RequisitionListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (status) params.set("status", status);
    if (search) params.set("search", search);

    return this.request<RequisitionListResponse>(
      `/api/v1/requisitions?${params.toString()}`
    );
  }

  async getRequisition(id: string): Promise<Requisition> {
    return this.request<Requisition>(`/api/v1/requisitions/${id}`);
  }

  async createRequisition(data: {
    title: string;
    job_description: string;
    location?: string;
  }): Promise<Requisition> {
    return this.request<Requisition>("/api/v1/requisitions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ── AI Extraction ────────────────────────────────────────────────────────

  async extractRequirements(jobDescription: string): Promise<JDExtractionResult> {
    return this.request<JDExtractionResult>(
      "/api/v1/requisitions/extract-requirements",
      {
        method: "POST",
        body: JSON.stringify({ job_description: jobDescription }),
      }
    );
  }

  // ── Scorecards ───────────────────────────────────────────────────────────

  async getScorecard(requisitionId: string): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard`
    );
  }

  async createScorecard(
    requisitionId: string,
    data: ScorecardCreate
  ): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecards`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async updateScorecard(
    requisitionId: string,
    data: ScorecardUpdate
  ): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      }
    );
  }

  async approveScorecard(requisitionId: string): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard/approve`,
      {
        method: "POST",
      }
    );
  }

  async duplicateScorecard(requisitionId: string): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard/duplicate`,
      {
        method: "POST",
      }
    );
  }
}

export const api = new ApiClient();
