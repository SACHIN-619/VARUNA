import React, { useEffect, useMemo, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { fetchDashboardSummary } from '../services/api';
import { DashboardSummary } from '../types';
import { SourceModeBadge } from '../components/shared/SourceModeBadge';
import { modelInfo } from '../utils/models';
import { ShieldAlert, ChevronRight, RefreshCw, CloudRain, Thermometer, Wind } from 'lucide-react';

/**
 * Extreme-weather guidance computed by the real pipeline: for every subdivision and hazard the fused
 * forecast is compared with IMD-aligned thresholds (stage 11). Nothing on this page is typed in by hand.
 */

type Hazard = 'rainfall' | 'temperature' | 'wind_speed';
type Level = 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'GREY';

const HAZARDS: Array<{ id: Hazard; label: string; icon: React.FC<{ className?: string }>; levels: Array<[Level, number, string]>; rule: string }> = [
  { id: 'rainfall', label: 'Heavy rainfall', icon: CloudRain,
    levels: [['YELLOW', 64.5, 'Heavy'], ['ORANGE', 115.6, 'Very heavy'], ['RED', 204.5, 'Extremely heavy']],
    rule: 'IMD 24 h rainfall: heavy ≥ 64.5 mm · very heavy ≥ 115.6 mm · extremely heavy ≥ 204.5 mm' },
  { id: 'temperature', label: 'Heat', icon: Thermometer,
    levels: [['ORANGE', 40, 'Heatwave'], ['RED', 45, 'Severe heatwave']],
    rule: 'IMD heatwave (plains): Tmax ≥ 40 °C · severe ≥ 45 °C' },
  { id: 'wind_speed', label: 'Wind', icon: Wind,
    levels: [['ORANGE', 14, 'Gale / squall'], ['RED', 24.5, 'Storm force']],
    rule: 'Gale / squall ≥ 14 m/s (≈ 50 km/h) · storm ≥ 24.5 m/s (≈ 88 km/h)' },
];

const RANK: Record<Level, number> = { GREY: -1, GREEN: 0, YELLOW: 1, ORANGE: 2, RED: 3 };
const CHIP: Record<Level, string> = {
  RED: 'bg-red-600 text-white border-red-700',
  ORANGE: 'bg-orange-500 text-white border-orange-600',
  YELLOW: 'bg-yellow-300 text-yellow-950 border-yellow-500',
  GREEN: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-500/40',
  GREY: 'bg-surface-container text-on-surface-variant border-outline-variant/40',
};

interface Cell { s: DashboardSummary | null; level: Level }
type Row = { id: string; name: string; cells: Record<Hazard, Cell>; worst: Level };

const levelOf = (s: DashboardSummary | null): Level => {
  const l = (s?.extreme_guidance as { alert_level?: string } | undefined)?.alert_level as Level | undefined;
  return l && l in RANK ? l : 'GREY';
};

export const ExtremeEventsPage: React.FC = () => {
  const { subdivisions, leadHours, weatherRegime, dataSourcePref } = useVaruna();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [sel, setSel] = useState<{ region: string; hazard: Hazard } | null>(null);
  const [stamp, setStamp] = useState<string>('');

  const load = async () => {
    setLoading(true);
    const out: Row[] = await Promise.all(subdivisions.map(async sd => {
      const cells = {} as Record<Hazard, Cell>;
      await Promise.all(HAZARDS.map(async h => {
        try {
          const s = await fetchDashboardSummary(sd.id, h.id, leadHours, weatherRegime, undefined, dataSourcePref);
          cells[h.id] = { s, level: levelOf(s) };
        } catch {
          cells[h.id] = { s: null, level: 'GREY' };
        }
      }));
      const worst = HAZARDS.map(h => cells[h.id].level).reduce((a, b) => (RANK[b] > RANK[a] ? b : a), 'GREY' as Level);
      return { id: sd.id, name: sd.name, cells, worst };
    }));
    out.sort((a, b) => RANK[b.worst] - RANK[a.worst] || a.name.localeCompare(b.name));
    setRows(out);
    setStamp(new Date().toISOString().replace('T', ' ').slice(0, 16) + ' UTC');
    const first = out.find(r => RANK[r.worst] > 0) || out[0];
    if (first) {
      const hz = HAZARDS.find(h => first.cells[h.id].level === first.worst)?.id || 'rainfall';
      setSel(prev => prev && out.some(r => r.id === prev.region) ? prev : { region: first.id, hazard: hz });
    }
    setLoading(false);
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [leadHours, weatherRegime, dataSourcePref, subdivisions.length]);

  const flagged = rows.filter(r => RANK[r.worst] > 0).length;
  const row = rows.find(r => r.id === sel?.region);
  const hz = HAZARDS.find(h => h.id === sel?.hazard) || HAZARDS[0];
  const cell = row?.cells[hz.id];
  const s = cell?.s || null;

  const detail = useMemo(() => {
    if (!s) return null;
    const watch = hz.levels[0][1];
    const models = Object.entries(s.model_forecasts || {}).filter(([, v]) => v !== null && v !== undefined) as Array<[string, number]>;
    const w = new Map<string, number>((s.weights || []).map(x => [String(x.model_id), x.weight]));
    const above = models.filter(([, v]) => v >= watch).sort((a, b) => b[1] - a[1]);
    const below = models.filter(([, v]) => v < watch).sort((a, b) => b[1] - a[1]);
    const wAbove = above.reduce((t, [m]) => t + (w.get(m) || 0), 0);
    const next = hz.levels.find(([, t]) => (s.fused_value ?? 0) < t);
    return { watch, above, below, w, wAbove, next };
  }, [s, hz]);
  const [lo, hi] = useMemo(() => {
    const v = Object.values(s?.model_forecasts || {}).filter((x): x is number => typeof x === 'number');
    return v.length ? [Math.min(...v), Math.max(...v)] : ['—', '—'];
  }, [s, hz]);

  return (
    <div className="flex flex-col gap-5 p-4 lg:p-6 w-full">
      <div className="flex flex-wrap items-start justify-between gap-3 pb-4 border-b border-outline-variant/30">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-xs font-mono text-rose-600 dark:text-rose-400 font-bold uppercase tracking-wider">Extreme-weather guidance</span>
            <SourceModeBadge />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">Extreme event risk matrix · +{leadHours} h</h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1 max-w-3xl">
            Every cell is the pipeline's fused forecast for that subdivision and hazard, compared with IMD thresholds in stage 11.
            Click a cell to see which models push it over the threshold and which hold it back.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className={`px-2.5 py-1 rounded border font-bold ${flagged ? 'bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border-rose-500/50' : 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-500/40'}`}>
            {loading ? 'computing…' : `${flagged} of ${rows.length} subdivisions flagged`}
          </span>
          <button onClick={load} className="flex items-center gap-1 px-2.5 py-1 rounded border border-outline-variant/40 hover:bg-surface-container text-on-surface" aria-label="Recompute">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Recompute
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
        <div className="xl:col-span-7 flex flex-col gap-3 min-w-0">
          <div className="rounded-xl bg-surface-container-lowest border border-outline-variant/30 overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-on-surface-variant border-b border-outline-variant/30">
                  <th className="text-left p-3 font-bold">Subdivision</th>
                  {HAZARDS.map(h => <th key={h.id} className="text-left p-3 font-bold"><span className="inline-flex items-center gap-1"><h.icon className="w-3.5 h-3.5" />{h.label}</span></th>)}
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map(r => (
                  <tr key={r.id} className={`border-b border-outline-variant/20 ${sel?.region === r.id ? 'bg-primary/5' : ''}`}>
                    <td className="p-3 font-bold text-on-surface whitespace-nowrap">{r.name}</td>
                    {HAZARDS.map(h => {
                      const c = r.cells[h.id];
                      const active = sel?.region === r.id && sel?.hazard === h.id;
                      return (
                        <td key={h.id} className="p-2">
                          <button onClick={() => setSel({ region: r.id, hazard: h.id })} aria-label={`${r.name} ${h.label}`}
                            className={`w-full text-left px-2 py-1.5 rounded border ${CHIP[c.level]} ${active ? 'ring-2 ring-primary ring-offset-1' : ''}`}>
                            <span className="font-bold">{c.s?.fused_value ?? '—'} {c.s?.unit || ''}</span>
                            <span className="block text-[10px] opacity-90">{c.level === 'GREEN' ? 'below threshold' : c.level === 'GREY' ? 'no data' : c.level}</span>
                          </button>
                        </td>
                      );
                    })}
                    <td className="p-2"><ChevronRight className={`w-4 h-4 ${sel?.region === r.id ? 'text-primary' : 'text-on-surface-variant'}`} /></td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr><td colSpan={5} className="p-6 text-center text-on-surface-variant">{loading ? 'Running the pipeline for every subdivision…' : 'No subdivisions available.'}</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/30 text-[11px] font-mono text-on-surface-variant flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div>
              Decision support only. Official warnings are issued by IMD (MoES). Colours follow IMD categories applied to VARUNA's fused value
              {stamp && <> · computed {stamp}</>}.
            </div>
          </div>
        </div>

        <div className="xl:col-span-5 min-w-0">
          {row && s && detail ? (
            <div className="p-5 rounded-xl bg-surface-container-lowest border border-outline-variant/30 flex flex-col gap-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-[11px] font-mono text-primary uppercase font-bold">Guidance dossier</div>
                  <h3 className="font-headline font-extrabold text-lg text-on-surface">{hz.label} · {row.name}</h3>
                  <div className="text-[11px] font-mono text-on-surface-variant">valid +{leadHours} h{s.issue_time ? ` · issued ${String(s.issue_time).replace('T', ' ').slice(0, 16)}` : ''}</div>
                </div>
                <span className={`px-2.5 py-1 rounded border text-xs font-mono font-bold ${CHIP[cell!.level]}`}>{cell!.level}</span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant/30">
                  <span className="text-on-surface-variant text-[10px] uppercase block">Fused</span>
                  <span className="font-bold text-on-surface text-base">{s.fused_value} {s.unit}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant/30">
                  <span className="text-on-surface-variant text-[10px] uppercase block">Threshold</span>
                  <span className="font-bold text-on-surface text-base">{detail.watch} {s.unit}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant/30">
                  <span className="text-on-surface-variant text-[10px] uppercase block">Confidence</span>
                  <span className="font-bold text-on-surface text-base">{Math.round((s.confidence_score ?? 0) * 100)}%</span>
                </div>
              </div>

              <div className="text-[11px] font-mono text-on-surface-variant">
                {hz.rule}.{' '}
                {detail.next ? <>Next level ({detail.next[2]}) at {detail.next[1]} {s.unit}: {(detail.next[1] - (s.fused_value ?? 0)).toFixed(1)} {s.unit} away.</> : <>Highest category reached.</>}
                {' '}Model disagreement: <strong className="text-on-surface">{s.disagreement?.disagreement_level}</strong> (spread {lo}–{hi} {s.unit}).
              </div>

              <div className="space-y-2 text-xs font-mono">
                <div className="p-3 rounded bg-rose-50 dark:bg-rose-950/30 border border-rose-500/30">
                  <span className="text-rose-700 dark:text-rose-400 font-bold block mb-1">At or above threshold · {Math.round(detail.wAbove * 100)}% of the trust weight</span>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.above.length ? detail.above.map(([m, v]) => (
                      <span key={m} className="px-2 py-0.5 rounded border border-rose-500/40 text-on-surface">{modelInfo(m, s.source_meta?.[m]).label} {v} · w {Math.round((detail.w.get(m) || 0) * 100)}%</span>
                    )) : <span className="text-on-surface-variant">none</span>}
                  </div>
                </div>
                <div className="p-3 rounded bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-500/30">
                  <span className="text-emerald-700 dark:text-emerald-400 font-bold block mb-1">Below threshold</span>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.below.length ? detail.below.map(([m, v]) => (
                      <span key={m} className="px-2 py-0.5 rounded border border-emerald-500/40 text-on-surface">{modelInfo(m, s.source_meta?.[m]).label} {v} · w {Math.round((detail.w.get(m) || 0) * 100)}%</span>
                    )) : <span className="text-on-surface-variant">none</span>}
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-surface-container-low border border-primary/30 text-xs text-on-surface leading-relaxed">
                <strong className="text-primary block mb-1">Why VARUNA says {cell!.level === 'GREEN' ? 'no extreme' : cell!.level}</strong>
                The fused value {s.fused_value} {s.unit} is Σ weight × forecast over {Object.keys(s.model_forecasts || {}).length} models.
                {detail.above.length > 0 && detail.below.length > 0 && <> Models disagree on the threshold, so confidence is {Math.round((s.confidence_score ?? 0) * 100)}% and the forecaster should watch the next run.</>}
                {detail.above.length === 0 && <> No model reaches the threshold.</>}
                {detail.below.length === 0 && detail.above.length > 0 && <> Every model is at or above the threshold.</>}
              </div>
            </div>
          ) : (
            <div className="p-8 rounded-xl bg-surface-container-lowest border border-outline-variant/30 text-center text-on-surface-variant font-mono text-xs">
              {loading ? 'Computing…' : 'Select a cell to see the guidance.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
