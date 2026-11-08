import type { TokenResponse } from "./types";

const ACCESS_TOKEN_KEY = "shortlist_access_token";
const REFRESH_TOKEN_KEY = "shortlist_refresh_token";

export function saveTokens(tokens: TokenResponse): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) return token;
  try {
    const params = new URLSearchParams(window.location.search);
    const paramToken = params.get("auth_token");
    if (paramToken) {
      localStorage.setItem(ACCESS_TOKEN_KEY, paramToken);
      return paramToken;
    }
  } catch {
    // ignore
  }
  return null;
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
