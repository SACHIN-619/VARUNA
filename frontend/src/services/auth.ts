/**
 * VARUNA Authentication Service
 * Handles JWT token lifecycle: login, logout, token persistence, and header injection.
 */

const TOKEN_KEY = 'varuna_access_token';
const USER_KEY  = 'varuna_user_profile';

export interface AuthUser {
  user_id: string;
  name: string;
  email: string;
  role: 'FORECASTER' | 'OPERATIONS' | 'ANALYST' | 'ADMIN' | 'AUDITOR';
  access_token: string;
  /** Permission strings from the backend role matrix (e.g. 'data:ingest', 'live:fetch'). */
  permissions?: string[];
  region_scope?: string[] | null;
  must_change_password?: boolean;
  offline?: boolean;
}

/** Offline demo sessions mirror the backend matrix so the UI hides what the API would refuse. */
export const OFFLINE_PERMISSIONS: Record<AuthUser['role'], string[]> = {
  FORECASTER: ['forecast:view', 'notifications:view', 'verification:view', 'verification:run', 'demo:inject'],
  OPERATIONS: ['forecast:view', 'notifications:view', 'verification:view', 'verification:run', 'demo:inject',
               'data:ingest', 'live:fetch', 'pipeline:operate'],
  ANALYST: ['forecast:view', 'notifications:view', 'verification:view', 'verification:run', 'demo:inject',
            'data:ingest', 'skill:update', 'experiment:run', 'change:propose', 'pipeline:operate'],
  ADMIN: ['forecast:view', 'notifications:view', 'verification:view', 'pipeline:operate', 'change:approve',
          'users:manage', 'config:view', 'audit:view', 'live:fetch', 'data:ingest', 'demo:inject'],
  AUDITOR: ['forecast:view', 'verification:view', 'audit:view', 'config:view', 'pipeline:operate'],
};

export class InvalidCredentialsError extends Error {}

const API = (): string => ((import.meta as any).env?.VITE_API_BASE as string) || '/api';
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

/**
 * Sign in. A hosted free-tier API can be asleep: the first requests then fail or return 502/503/504 for up to
 * a minute. Keep retrying for WAKE_TIMEOUT_MS (reporting progress) before falling back to the offline demo.
 */
const WAKE_TIMEOUT_MS = 75_000;

export async function loginUser(email: string, password: string, onStatus?: (msg: string) => void): Promise<AuthUser> {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  const t0 = Date.now();
  let res: Response | null = null;
  for (let attempt = 0; ; attempt++) {
    try {
      res = await fetch(`${API()}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });
      if (![502, 503, 504].includes(res.status)) break;
    } catch (e) {
      res = null;
    }
    const waited = Date.now() - t0;
    if (waited > WAKE_TIMEOUT_MS) break;
    onStatus?.(`Waking the server… ${Math.round(waited / 1000)} s (a sleeping free-tier server takes up to a minute)`);
    await sleep(attempt < 2 ? 2000 : 5000);
  }
  if (!res || [502, 503, 504].includes(res.status)) {
    // Backend still unreachable -> offline demo session (clearly marked, read-only)
    console.warn('Backend API unreachable, starting offline demo session.');
    return offlineDemoLogin(email);
  }

  {
    if (res.ok) {
      const data = await res.json();
      const user: AuthUser = {
        user_id:      data.user_id,
        name:         data.name,
        email:        data.email,
        role:         data.role,
        access_token: data.access_token,
        permissions:  data.permissions || OFFLINE_PERMISSIONS[data.role as AuthUser['role']] || [],
        region_scope: data.region_scope ?? ['*'],
        must_change_password: !!data.must_change_password,
      };

      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return user;
    }
    // SECURITY FIX: a 401/403 used to fall through to the demo fallback, so ANY password logged in.
    if (res.status === 401 || res.status === 403 || res.status === 422) {
      throw new InvalidCredentialsError('Invalid email or password.');
    }
    if (res.status >= 500 || res.status === 404) {
      // API route missing or backend error -> offline demo (read-only)
      return offlineDemoLogin(email);
    }
    throw new InvalidCredentialsError(`Sign-in failed (HTTP ${res.status}).`);
  }
}

function offlineDemoLogin(email: string): AuthUser {
  let role: AuthUser['role'] = 'FORECASTER';
  const lower = email.toLowerCase();
  if (lower.includes('ops')) role = 'OPERATIONS';
  else if (lower.includes('analyst')) role = 'ANALYST';
  else if (lower.includes('admin')) role = 'ADMIN';
  else if (lower.includes('audit')) role = 'AUDITOR';

  const user: AuthUser = {
    user_id: 'usr_' + Math.random().toString(36).substring(2, 8),
    name: email.split('@')[0].toUpperCase().replace('.', ' '),
    email: email,
    role: role,
    access_token: 'offline_demo_' + Date.now(),
    // Read-only: with no backend nothing can be saved, so no upload / fetch / verify controls are offered
    permissions: OFFLINE_PERMISSIONS[role].filter(p => p === 'forecast:view' || p === 'verification:view'),
    region_scope: ['*'],
    offline: true,
  };

  localStorage.setItem(TOKEN_KEY, user.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

export const SESSION_EXPIRED_EVENT = 'varuna:session-expired';

/**
 * Watch API responses: a 401 on a request that carried our token means the session is no longer valid
 * (expired after 24 h, signed by a different server key, or an offline demo token). The dashboard then asks
 * the user to sign in again instead of showing raw "Authentication required" errors.
 */
export function installSessionWatcher(): void {
  const w = window as any;
  if (w.__varunaFetchWatched) return;
  w.__varunaFetchWatched = true;
  const orig = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const res = await orig(input, init);
    try {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
      const h = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined));
      if (res.status === 401 && h.has('Authorization') && url.includes('/api/') && !url.includes('/auth/login')) {
        window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
      }
    } catch { /* never break the request */ }
    return res;
  };
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    const u = JSON.parse(raw) as AuthUser;
    // sessions stored by an older build have no permission list
    if (!u.permissions) u.permissions = OFFLINE_PERMISSIONS[u.role] || [];
    // offline sessions stored by an older build carried write permissions they could never use
    if (u.offline) u.permissions = u.permissions.filter(p => p === 'forecast:view' || p === 'verification:view');
    return u;
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function logoutUser(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

/** Returns Authorization header value for API calls */
export function authHeader(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function hasPermission(user: AuthUser | null, perm: string): boolean {
  return !!user && (user.permissions || []).includes(perm);
}
