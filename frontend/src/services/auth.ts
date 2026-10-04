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

export async function loginUser(email: string, password: string): Promise<AuthUser> {
  let res: Response;
  try {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    res = await fetch(`${((import.meta as any).env?.VITE_API_BASE as string) || '/api'}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });
  } catch (e) {
    // Backend unreachable -> offline demo session (clearly marked, read-only demo data)
    console.warn('Backend API unreachable, starting offline demo session.', e);
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
    if (res.status >= 500 || res.status === 404 || res.status === 502) {
      // API gateway up but backend down -> offline demo
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
    permissions: OFFLINE_PERMISSIONS[role],
    region_scope: ['*'],
    offline: true,
  };

  localStorage.setItem(TOKEN_KEY, user.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    const u = JSON.parse(raw) as AuthUser;
    // sessions stored by an older build have no permission list
    if (!u.permissions) u.permissions = OFFLINE_PERMISSIONS[u.role] || [];
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
