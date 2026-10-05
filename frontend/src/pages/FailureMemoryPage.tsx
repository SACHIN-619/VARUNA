import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { modelInfo } from '../utils/models';
import { BrainCircuit, TrendingUp, TrendingDown, Minus, RefreshCw, Info } from 'lucide-react';

const API_BASE: string = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';

/**
 * Trust drift from stored verification history (GET /api/verification/drift).
 * Every row is computed from verified forecast errors; nothing on this page is typed in by hand.
 */

type Status = 'DEGRADING' | 'IMPROVING' | 'STABLE' | 'INSUFFICIENT_HISTORY';
interface DriftItem {
  region_id: string; model_id: string; lead_hours: number; n: number; errors: number[]; references: string[];
  first_valid: string | null; last_valid: string | null; status: Status;
  baseline_mae: number | null; recent_mae: number | null; ratio: number | null; recent_bias: number | null; needed?: number;
}
interface DriftResponse {
  variable: string; rule: { recent: number; min_baseline: number; ratio_threshold: number; unit_floor: number };
  counts: Record<Status, number>; items: DriftItem[];
}

const UNIT: Record<string, string> = { rainfall: 'mm', temperature: '°C', wind_speed: 'm/s' };
const REF: Record<string, string> = {
  LIVE_BACKFILL_IMD: 'IMD gridded', LIVE_BACKFILL_ERA5: 'ERA5', canonical_pipeline: 'stage-14 verify', operational_cycle: 'operational cycle',
};
const CHIP: Record<Status, string> = {
  DEGRADING: 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border-rose-500/50',
  IMPROVING: 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border-emerald-500/50',
  STABLE: 'bg-surface-container text-on-surface border-outline-variant/50',
  INSUFFICIENT_HISTORY: 'bg-surface-container-low text-on-surface-variant border-outline-variant/30',
};

const Spark: React.FC<{ errors: number[]; recent: number; status: Status }> = ({ errors, recent, status }) => {
  if (errors.length < 2) return <span className="text-on-surface-variant">—</span>;
  const w = 160, h = 34, max = Math.max(...errors, 0.01);
  const x = (i: number) => (i / (errors.length - 1)) * (w - 4) + 2;
  const y = (v: number) => h - 3 - (v / max) * (h - 6);
  const pts = errors.map((e, i) => `${x(i).toFixed(1)},${y(e).toFixed(1)}`).join(' ');
  const split = Math.max(0, errors.length - recent);
  const stroke = status === 'DEGRADING' ? '#e11d48' : status === 'IMPROVING' ? '#059669' : '#0284c7';
  return (
    <svg width={w} height={h} role="img" aria-label={`absolute error over ${errors.length} verified cases`}>
      {status !== 'INSUFFICIENT_HISTORY' && <rect x={x(split)} y={0} width={w - x(split)} height={h} fill={stroke} opacity={0.08} />}
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth={1.6} />
    </svg>
  );
};

export const FailureMemoryPage: React.FC = () => {
  const { variable, subdivisions } = useVaruna();
  const [data, setData] = useState<DriftResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAll, setShowAll] = useState(false);

  const load = async () => {
    setLoading(true); setErr(null);
    try {
      const r = await fetch(`${API_BASE}/verification/drift?variable=${variable}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e) {
      setErr(`Drift could not be computed: ${(e as Error).message}. The backend may be unreachable.`);
      setData(null);
    }
    setLoading(false);
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [variable]);

  const name = (id: string) => subdivisions.find(s => s.id === id)?.name || id.replace('IN_', '').replace(/_/g, ' ');
  const unit = UNIT[variable] || '';
  const items = (data?.items || []).filter(i => showAll || i.status !== 'INSUFFICIENT_HISTORY');
  const rule = data?.rule;

  return (
    <div className="flex flex-col gap-5 p-4 lg:p-6 w-full">
      <div className="flex flex-wrap items-start justify-between gap-3 pb-4 border-b border-outline-variant/30">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1 text-xs font-mono text-primary font-bold uppercase tracking-wider">
            <BrainCircuit className="w-4 h-4" /> Failure memory · trust drift
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">Is any model getting worse?</h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1 max-w-3xl">
            For every model, region and lead time, the error of the most recent verified cases is compared with that model's own earlier record.
            A drift flag asks for review; it never removes a model by itself. Skill memory, and therefore the next weights, already absorb these errors.
          </p>
        </div>
        <button onClick={load} className="flex items-center gap-1 px-2.5 py-1 rounded border border-outline-variant/40 hover:bg-surface-container text-on-surface font-mono text-xs">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Recompute
        </button>
      </div>

      {rule && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
          {([['DEGRADING', TrendingUp], ['IMPROVING', TrendingDown], ['STABLE', Minus], ['INSUFFICIENT_HISTORY', Info]] as Array<[Status, React.FC<{ className?: string }>]>).map(([s, Icon]) => (
            <div key={s} className={`p-3 rounded-lg border ${CHIP[s]}`}>
              <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold"><Icon className="w-3.5 h-3.5" />{s.replace('_', ' ').toLowerCase()}</div>
              <div className="text-2xl font-bold mt-1">{data?.counts[s] ?? 0}</div>
            </div>
          ))}
        </div>
      )}

      {rule && (
        <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/30 text-[11px] font-mono text-on-surface-variant">
          Rule: recent MAE = mean |error| of the last {rule.recent} verified cases; baseline = all earlier cases (at least {rule.min_baseline}).
          Degrading when recent ≥ {rule.ratio_threshold}× baseline and at least {rule.unit_floor} {unit} worse; improving when the reverse holds.
        </div>
      )}

      {err && <div className="p-4 rounded-lg border border-error/40 text-error font-mono text-xs">{err}</div>}

      {data && (
        <div className="rounded-xl bg-surface-container-lowest border border-outline-variant/30 overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-left text-on-surface-variant border-b border-outline-variant/30">
                <th className="p-3">Model</th><th className="p-3">Region</th><th className="p-3">Lead</th><th className="p-3">Status</th>
                <th className="p-3 text-right">Baseline MAE</th><th className="p-3 text-right">Recent MAE</th><th className="p-3 text-right">Recent bias</th>
                <th className="p-3">|error| over time (shaded = recent)</th><th className="p-3">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {items.map(i => (
                <tr key={`${i.region_id}-${i.model_id}-${i.lead_hours}`} className="border-b border-outline-variant/20">
                  <td className="p-3 font-bold text-on-surface whitespace-nowrap">{modelInfo(i.model_id).label}</td>
                  <td className="p-3 whitespace-nowrap">{name(i.region_id)}</td>
                  <td className="p-3 whitespace-nowrap">+{i.lead_hours} h</td>
                  <td className="p-3"><span className={`px-2 py-0.5 rounded border font-bold whitespace-nowrap ${CHIP[i.status]}`}>
                    {i.status === 'INSUFFICIENT_HISTORY' ? `needs ${i.needed} cases` : i.status}{i.ratio && i.status !== 'STABLE' ? ` ×${i.ratio}` : ''}</span></td>
                  <td className="p-3 text-right">{i.baseline_mae ?? '—'}</td>
                  <td className="p-3 text-right font-bold text-on-surface">{i.recent_mae ?? '—'}</td>
                  <td className="p-3 text-right">{i.recent_bias === null ? '—' : `${i.recent_bias > 0 ? '+' : ''}${i.recent_bias}`}</td>
                  <td className="p-3"><Spark errors={i.errors} recent={rule?.recent || 7} status={i.status} /></td>
                  <td className="p-3 text-on-surface-variant whitespace-nowrap">
                    {i.n} cases · {i.references.map(r => REF[r] || r).join(', ')}
                    {i.first_valid && <div className="text-[10px]">{i.first_valid.slice(0, 10)} → {i.last_valid?.slice(0, 10)}</div>}
                  </td>
                </tr>
              ))}
              {!items.length && (
                <tr><td colSpan={9} className="p-6 text-center text-on-surface-variant">
                  {data.items.length
                    ? 'Every model/region/lead still has too little verified history for a drift test.'
                    : 'No verified history for this variable yet.'}{' '}
                  Build it with Data sources → Run backfill (truth: IMD gridded), or verify runs in pipeline stage 14.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {data && data.counts.INSUFFICIENT_HISTORY > 0 && (
        <button onClick={() => setShowAll(s => !s)} className="self-start text-xs font-mono text-primary underline">
          {showAll ? 'Hide' : 'Show'} {data.counts.INSUFFICIENT_HISTORY} combination(s) with too little history
        </button>
      )}
    </div>
  );
};
