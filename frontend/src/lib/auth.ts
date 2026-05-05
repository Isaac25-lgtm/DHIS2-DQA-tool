import type { UserRole } from "../types";

const TOKEN_STORAGE_KEY = "ucmb_dqa_access_token";

export function getAccessToken(): string | null {
  const token = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    return token;
  }

  // Clean up tokens saved by older builds without continuing to use them.
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  return null;
}

export function setAccessToken(token: string) {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) {
      return null;
    }
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const decoded = window.atob(padded);
    return JSON.parse(decoded) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getAccessTokenExpiry(token: string | null): number | null {
  if (!token) {
    return null;
  }
  const payload = decodeJwtPayload(token);
  const exp = payload?.exp;
  return typeof exp === "number" ? exp : null;
}

export function isAccessTokenExpired(token: string | null) {
  const expiry = getAccessTokenExpiry(token);
  if (!expiry) {
    return true;
  }
  return Date.now() >= expiry * 1000;
}

export function hasValidAccessToken() {
  const token = getAccessToken();
  return Boolean(token) && !isAccessTokenExpired(token);
}

export function hasAnyRole(currentRole: UserRole | undefined, allowedRoles: UserRole[]) {
  if (!currentRole) {
    return false;
  }
  return allowedRoles.includes(currentRole);
}
