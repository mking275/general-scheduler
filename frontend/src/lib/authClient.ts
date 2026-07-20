/**
 * authClient — VetAgent staff/owner-side auth against the vendored cos_identity
 * (C7) component. Implements the component's client contract (vendoring.md §5):
 *
 *   - store BOTH the access and refresh tokens; attach the access token as a
 *     `Authorization: Bearer` header;
 *   - refresh ROTATES: every /api/auth/refresh returns a NEW refresh token and
 *     revokes the old one, so we MUST persist the returned pair each time;
 *   - dedup refresh: a single in-flight refresh promise is shared so concurrent
 *     401s yield exactly one new session;
 *   - 401 interceptor: on 401, attempt one refresh then retry once; on repeated
 *     401, clear tokens and signal sign-in.
 *
 * Provider is the FAKE provider (Firebase deferred): "login" exchanges a
 * deterministic fake external token for an internal session. This is the
 * staff/owner surface only — pet-owner identity stays on the 011 ladder.
 */

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

const ACCESS_KEY = "vetagent.identity.access";
const REFRESH_KEY = "vetagent.identity.refresh";

export interface SessionPair {
  access_token: string;
  refresh_token: string;
}

export interface AuthUser {
  id: string;
  email: string;
  role: string;
  customer_id?: string | null;
  customer_role?: string;
  status?: string;
}

function isBrowser(): boolean {
  return typeof window !== "undefined" && !!window.localStorage;
}

export function getAccessToken(): string | null {
  return isBrowser() ? window.localStorage.getItem(ACCESS_KEY) : null;
}

export function getRefreshToken(): string | null {
  return isBrowser() ? window.localStorage.getItem(REFRESH_KEY) : null;
}

/** Persist a freshly returned pair. Called on login AND on every rotation. */
export function storePair(pair: SessionPair): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_KEY, pair.access_token);
  window.localStorage.setItem(REFRESH_KEY, pair.refresh_token);
}

export function clearTokens(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

/** Build the fake provider's external token (fake:uid|email|provider|name). */
function makeFakeExternalToken(email: string, displayName = ""): string {
  const uid = `staff-${email.toLowerCase()}`;
  return `fake:${uid}|${email}|google|${displayName}`;
}

/**
 * Sign in via the fake provider: exchange an external token for an internal
 * session pair and persist it. Returns the authenticated user.
 */
export async function login(
  email = "demo@clinic.com",
  displayName = "Demo Staff",
): Promise<AuthUser> {
  const res = await fetch(`${API}/api/auth/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ external_token: makeFakeExternalToken(email, displayName) }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Sign-in failed (${res.status}): ${detail}`);
  }
  const body = await res.json();
  storePair({ access_token: body.access_token, refresh_token: body.refresh_token });
  return body.user as AuthUser;
}

// Shared in-flight refresh promise (dedup): concurrent callers await one refresh.
let inflightRefresh: Promise<string | null> | null = null;

/**
 * Rotate the stored refresh token into a new pair and persist it. Concurrent
 * callers share one in-flight request. Returns the new access token, or null if
 * refresh failed (tokens are cleared in that case).
 */
export function refresh(): Promise<string | null> {
  if (inflightRefresh) return inflightRefresh;

  inflightRefresh = (async () => {
    const current = getRefreshToken();
    if (!current) return null;
    try {
      const res = await fetch(`${API}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: current }),
      });
      if (!res.ok) {
        clearTokens();
        return null;
      }
      const pair = (await res.json()) as SessionPair;
      // ROTATION: persist the NEW pair (the old refresh token is now revoked).
      storePair(pair);
      return pair.access_token;
    } catch {
      return null;
    } finally {
      inflightRefresh = null;
    }
  })();

  return inflightRefresh;
}

/**
 * fetch() with the access token attached and a 401 interceptor: on 401, refresh
 * once and retry; on repeated 401, clear tokens and rethrow so the caller can
 * route to sign-in. Does NOT intercept the refresh endpoint itself.
 */
export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const withAuth = (token: string | null): RequestInit => ({
    ...init,
    headers: {
      ...(init.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  let res = await fetch(input, withAuth(getAccessToken()));
  if (res.status !== 401) return res;

  const newAccess = await refresh();
  if (!newAccess) {
    clearTokens();
    return res; // still 401 — caller routes to sign-in
  }
  res = await fetch(input, withAuth(newAccess));
  return res;
}

/** Revoke the refresh token server-side and clear local tokens. */
export async function logout(): Promise<void> {
  const current = getRefreshToken();
  if (current) {
    try {
      await fetch(`${API}/api/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: current }),
      });
    } catch {
      // best-effort; clear locally regardless
    }
  }
  clearTokens();
}
