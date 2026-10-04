/**
 * Client for the governance / live-data / notification / audit endpoints.
 * Every call sends the JWT; errors surface the backend's `detail` message.
 */
import { authHeader } from './auth';

const API_BASE: string = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function call<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...authHeader(), ...(init.headers || {}) },
    });
  } catch {
    throw new ApiError(0, 'Backend unreachable.');
  }
  const text = await res.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const d = data && (data.detail ?? data.message);
    const msg = typeof d === 'string' ? d : Array.isArray(d) ? d.map((x: any) => x.msg || JSON.stringify(x)).join('; ') : `HTTP ${res.status}`;
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

const post = <T = any>(path: string, body?: unknown) => call<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });
const patch = <T = any>(path: string, body?: unknown) => call<T>(path, { method: 'PATCH', body: JSON.stringify(body) });

// ── Live public data ────────────────────────────────────────────────────────────
export interface LiveCatalog {
  enabled: boolean; status: string; attribution: string; licence: string;
  public_models: Array<{ slot: string; open_meteo_id: string; name: string; provider: string; kind: string; resolution: string; note?: string }>;
  restricted_models: Array<{ slot: string; how_to_get: string }>;
  reference: { id: string; name: string; latency_days: number; note: string };
  endpoints: Record<string, string>;
}
export const getLiveCatalog = () => call<LiveCatalog>('/live/sources');
export const liveFetch = (region_id: string, variables: string[], days = 4) =>
  post('/live/fetch', { region_id, variables, days });
export const liveBackfill = (region_id: string, variable: string, days = 45, truth_source = 'AUTO') =>
  post('/live/backfill', { region_id, variable, days, lead_days: [1, 2], truth_source });

// ── India-first sources ─────────────────────────────────────────────────────────
export interface IndiaSource { id: string; name: string; provider: string; role: string; access: string; status: string; detail: string; url: string; cached_files?: number }
export interface IndiaCatalog {
  tiers: string[]; india_primary: IndiaSource[]; station_map: Record<string, { station: string; name?: string }>;
  attribution: string;
  global_reference: { status: string; enabled: boolean; note: string; licence: string; attribution: string;
                      models: Array<{ slot: string; name: string; provider: string; resolution: string; note?: string }> };
  restricted: Array<{ slot: string; how_to_get: string }>;
}
export const getIndiaSources = () => call<IndiaCatalog>('/india/sources');
export const imdGridFetch = (region_id: string, variable: string, start: string, end?: string) =>
  post('/india/imd-grid/fetch', { region_id, variable, start, end });
export const ncmrwfScan = () => post('/india/ncmrwf/scan');
export const imdObservation = (region_id: string) => call(`/india/imd/observation?region_id=${encodeURIComponent(region_id)}`);
export async function imdGridUpload(file: File, variable: string, kind: string, key: string) {
  const fd = new FormData();
  fd.append('file', file); fd.append('variable', variable); fd.append('kind', kind); fd.append('key', key);
  const res = await fetch(`${API_BASE}/india/imd-grid/upload`, { method: 'POST', body: fd, headers: { ...authHeader() } });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, (data && data.detail) || `HTTP ${res.status}`);
  return data;
}
export const liveDatasets = () => call<any[]>('/live/datasets');

// ── Notifications ───────────────────────────────────────────────────────────────
export interface NotificationRule {
  rule: string; formula: string; values: Record<string, any>; computation: string; triggered: boolean;
}
export interface NotificationSource {
  model_id: string; value: number | null; source: string; provenance?: string | null; dataset_id?: string | null;
  issue_time?: string | null; received_at?: string | null; weight?: number | null;
}
export interface VarunaNotification {
  id: string; created_at: string; severity: 'INFO' | 'WARNING' | 'CRITICAL'; category: string; title: string;
  message: string; region_id?: string; variable?: string; lead_hours?: number; read: boolean;
  math?: { rules: NotificationRule[]; source_mode: string; strategy?: string; previous_at?: string; current_at?: string };
  sources?: { previous?: NotificationSource[]; current?: NotificationSource[] };
  snapshots?: Record<string, any>;
}
export const listNotifications = (limit = 30) => call<{ unread: number; items: VarunaNotification[] }>(`/notifications?limit=${limit}`);
export const getNotification = (id: string) => call<VarunaNotification>(`/notifications/${id}`);
export const markNotificationRead = (id: string) => post(`/notifications/${id}/read`);
export const markAllNotificationsRead = () => post('/notifications/read-all');

// ── Verification / skill memory ───────────────────────────────────────────────────
export const verifyRun = (body: Record<string, any>) => post('/verification/verify-run', body);
export const updateSkillMemory = (p: { region_id: string; variable: string; lead_hours: number; season?: string; weather_regime?: string }) =>
  post(`/verification/feedback-loop?${new URLSearchParams(Object.entries(p).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])).toString()}`);

// ── Audit ───────────────────────────────────────────────────────────────────────
export const listAuditEvents = (params: Record<string, string | number> = {}) =>
  call<{ total: number; items: any[] }>(`/audit/events?${new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()}`);
export const verifyAuditChain = () => call<{ intact: boolean; checked?: number; head_hash?: string; broken_at_seq?: number; reason?: string }>('/audit/verify-chain');

// ── Governance & users ──────────────────────────────────────────────────────────
export const getGovernanceConfig = () => call<{ config: Record<string, any>; change_types: Record<string, string> }>('/governance/config');
export const listProposals = () => call<any[]>('/governance/proposals');
export const createProposal = (change_type: string, payload: Record<string, any>, justification: string) =>
  post('/governance/proposals', { change_type, payload, justification });
export const approveProposal = (id: string, reason: string) => post(`/governance/proposals/${id}/approve`, { reason });
export const rejectProposal = (id: string, reason: string) => post(`/governance/proposals/${id}/reject`, { reason });
export const listUsers = () => call<any[]>('/auth/users');
export const createUser = (body: Record<string, any>) => post('/auth/users', body);
export const updateUser = (id: string, body: Record<string, any>) => patch(`/auth/users/${id}`, body);
export const getRoleMatrix = () => call<{ roles: string[]; permissions: Record<string, string>; matrix: Record<string, string[]> }>('/auth/roles');
