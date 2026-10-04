import { SourceMeta } from '../types';

export interface ModelInfo { label: string; role: string; bar: string; hex: string }

const INFO: Record<string, ModelInfo> = {
  NCUM: { label: 'NCUM (NCMRWF)', role: 'Indian operational NWP', bar: 'bg-gradient-to-r from-sky-600 to-cyan-500 text-sky-100 border-sky-400/40', hex: '#0284c7' },
  WRF: { label: 'WRF (IMD, high-res)', role: 'Orographic / convective', bar: 'bg-gradient-to-r from-teal-600 to-emerald-500 text-teal-100 border-teal-400/40', hex: '#059669' },
  AI_WEATHER: { label: 'AI weather model', role: 'Machine-learning global model', bar: 'bg-gradient-to-r from-indigo-600 to-purple-500 text-indigo-100 border-indigo-400/40', hex: '#6366f1' },
  GFS: { label: 'NOAA GFS', role: 'Global NWP (NOAA)', bar: 'bg-gradient-to-r from-amber-600 to-orange-500 text-amber-100 border-amber-400/40', hex: '#d97706' },
  ECMWF_IFS: { label: 'ECMWF IFS', role: 'Global NWP (ECMWF open data)', bar: 'bg-gradient-to-r from-rose-600 to-pink-500 text-rose-100 border-rose-400/40', hex: '#e11d48' },
  UKMO_UM: { label: 'UK Met Office UM', role: 'Global NWP (UM family; not NCUM)', bar: 'bg-gradient-to-r from-lime-600 to-green-500 text-lime-100 border-lime-400/40', hex: '#65a30d' },
  ICON: { label: 'DWD ICON', role: 'Global NWP (Germany)', bar: 'bg-gradient-to-r from-slate-600 to-zinc-500 text-slate-100 border-slate-400/40', hex: '#64748b' },
};

/** Label/colour for any model slot. With live source metadata the label names the real product (e.g. AIFS). */
export function modelInfo(id: string, meta?: SourceMeta): ModelInfo {
  const base = INFO[id] || { label: id, role: 'Ensemble member', bar: 'bg-slate-600 text-white border-outline-variant', hex: '#475569' };
  if (meta?.source?.startsWith('OPEN_METEO:')) {
    const product = meta.source.split(':')[1];
    if (id === 'AI_WEATHER' && product.includes('aifs')) return { ...base, label: 'ECMWF AIFS (AI)', role: 'ML global model · public API' };
    return { ...base, role: `${base.role} · public API` };
  }
  return base;
}

export const fmtTime = (iso?: string | null): string => {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  if (isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
};

export const PROVENANCE_LABEL: Record<string, string> = {
  PUBLIC_API_FORECAST: 'Public model API',
  REANALYSIS_REFERENCE: 'ERA5 reanalysis (fallback truth)',
  OBSERVATION_GRIDDED: 'IMD gridded observation',
  SYNTHETIC_DEMO_SCENARIO: 'Synthetic demo',
  SYNTHETIC_DEMO: 'Synthetic demo',
  SYNTHETIC_STRESS_TEST: 'Synthetic test data',
  PUBLIC_BENCHMARK: 'Uploaded file',
  AUTHORIZED_OPERATIONAL_FEED: 'NCMRWF / IMD authorised feed',
};
