import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, MinusCircle, XCircle, Clock, RefreshCw, X, ArrowRight, Play, Database } from 'lucide-react';
import { useVaruna } from '../../context/VarunaContext';
import { StageTraceItem } from '../../types';
import { verifyRun, updateSkillMemory } from '../../services/platform';
import { fmtTime } from '../../utils/models';

/** Where each stage's evidence lives in the UI. */
const STAGE_ROUTE: Record<string, { route: string; label: string }> = {
  INGEST: { route: 'live-data', label: 'Data sources' },
  QC: { route: 'data-health', label: 'Data health' },
  HARMONIZE: { route: 'provenance', label: 'Provenance' },
  CONTEXT: { route: 'regional', label: 'Regional context' },
  SKILL: { route: 'model-performance', label: 'Model performance' },
  DISAGREEMENT: { route: 'fusion', label: 'Fusion centre' },
  TRUST: { route: 'trust-map', label: 'Trust map' },
  WEIGHTED_DISAGREEMENT: { route: 'fusion', label: 'Fusion centre' },
  FUSION: { route: 'fusion', label: 'Fusion centre' },
  UNCERTAINTY: { route: 'forecast', label: 'Forecast intelligence' },
  EXTREME: { route: 'extremes', label: 'Extreme events' },
  XAI: { route: 'why-this-forecast', label: 'Why this forecast' },
  PACKAGE: { route: 'provenance', label: 'Provenance' },
  VERIFY: { route: 'verification', label: 'Verification centre' },
};

const statusStyle = (s: string) => ({
  PASS: 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-500/30 text-emerald-700 dark:text-emerald-400',
  WARN: 'bg-amber-50 dark:bg-amber-950/40 border-amber-500/40 text-amber-700 dark:text-amber-400',
  FAIL: 'bg-rose-50 dark:bg-rose-950/40 border-rose-500/40 text-rose-700 dark:text-rose-400',
  PENDING: 'bg-sky-50 dark:bg-sky-950/40 border-sky-500/40 text-sky-700 dark:text-sky-400',
}[s] || 'bg-surface-container/60 border-outline-variant/50 text-on-surface-variant');

const StatusIcon: React.FC<{ s: string }> = ({ s }) =>
  s === 'PASS' ? <CheckCircle2 className="w-3.5 h-3.5" /> :
  s === 'WARN' ? <AlertTriangle className="w-3.5 h-3.5" /> :
  s === 'FAIL' ? <XCircle className="w-3.5 h-3.5" /> :
  s === 'PENDING' ? <Clock className="w-3.5 h-3.5" /> : <MinusCircle className="w-3.5 h-3.5" />;

const KV: React.FC<{ data: Record<string, any> }> = ({ data }) => {
  const entries = Object.entries(data || {});
  if (!entries.length) return <div className="text-on-surface-variant">—</div>;
  return (
    <div className="space-y-0.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-outline-variant/15 py-0.5">
          <span className="text-on-surface-variant shrink-0">{k}</span>
          <span className="text-on-surface text-right break-all">
            {v === null || v === undefined ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v)}
          </span>
        </div>
      ))}
    </div>
  );
};

const VerifyPanel: React.FC = () => {
  const { summary, regionId, variable, leadHours, weatherRegime, can, refreshData, dataSourcePref } = useVaruna();
  const [obs, setObs] = useState('');
  const [obsSrc, setObsSrc] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [skillMsg, setSkillMsg] = useState<string | null>(null);

  const run = async (ref: 'manual' | 'imd' | 'era5') => {
    setBusy(true); setError(null); setResult(null); setSkillMsg(null);
    try {
      const r = await verifyRun({
        region_id: regionId, variable, lead_hours: leadHours, weather_regime: weatherRegime, source: dataSourcePref,
        strategy: summary.strategy, use_imd: ref === 'imd', use_era5: ref === 'era5',
        observed_value: ref === 'manual' ? Number(obs) : undefined, observation_source: obsSrc || 'MANUAL_ENTRY',
      });
      setResult(r);
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };

  const skill = async () => {
    setBusy(true); setSkillMsg(null);
    try {
      const r = await updateSkillMemory({ region_id: summary.region_id || regionId, variable, lead_hours: leadHours, weather_regime: weatherRegime });
      const n = Object.values<any>(r.updated_model_skills || {}).filter((x: any) => x && x.sample_count > 0).length;
      setSkillMsg(`Skill memory updated for ${n} model(s). Next run uses the new MAE.`);
      refreshData();
    } catch (e: any) { setSkillMsg(e.message); } finally { setBusy(false); }
  };

  if (!can('verification:run')) {
    return <div className="text-on-surface-variant">Your role can view verification but not record observations.</div>;
  }
  return (
    <div className="space-y-2">
      <div className="text-on-surface-variant">
        This forecast is valid in the future, so stage 14 waits for an observation. Record one now (gauge / AWS / bulletin)
        or look up the IMD gridded value (published ~2 days after the valid day; ERA5 ~6 days, as a fallback).
      </div>
      <div className="flex flex-wrap gap-1.5 items-end">
        <label className="flex flex-col gap-0.5">
          <span className="text-[10px] text-on-surface-variant">Observed ({summary.unit})</span>
          <input value={obs} onChange={e => setObs(e.target.value)} inputMode="decimal" className="w-24 px-2 py-1 rounded border border-outline-variant/40 bg-surface text-on-surface" />
        </label>
        <label className="flex flex-col gap-0.5 flex-1 min-w-[120px]">
          <span className="text-[10px] text-on-surface-variant">Observation source</span>
          <input value={obsSrc} onChange={e => setObsSrc(e.target.value)} placeholder="e.g. IMD ARG station id" className="px-2 py-1 rounded border border-outline-variant/40 bg-surface text-on-surface" />
        </label>
        <button disabled={busy || obs === '' || isNaN(Number(obs))} onClick={() => run('manual')}
          className="px-2.5 py-1 rounded bg-primary text-on-primary font-bold disabled:opacity-40">Verify</button>
        <button disabled={busy} onClick={() => run('imd')} title="IMD Pune gridded daily rainfall / Tmax"
          className="px-2.5 py-1 rounded border border-primary/40 text-primary font-bold disabled:opacity-40">Use IMD grid</button>
        <button disabled={busy} onClick={() => run('era5')} title="Global reanalysis fallback"
          className="px-2 py-1 rounded border border-outline-variant/40 text-on-surface-variant disabled:opacity-40">ERA5</button>
      </div>
      {error && <div className="text-error">{error}</div>}
      {result && (
        <div className="rounded border border-outline-variant/30 p-2 space-y-1">
          <div className="font-bold">{result.status}{result.valid_day ? ` · valid ${result.valid_day}` : ''}</div>
          {result.message && <div className="text-on-surface-variant">{result.message}</div>}
          {result.forecast_errors && (
            <table className="w-full text-[10px] [&_th]:px-1.5 [&_td]:px-1.5">
              <thead><tr className="text-on-surface-variant"><th className="text-left">model</th><th className="text-right">error</th><th className="text-right">|error|</th></tr></thead>
              <tbody>{Object.entries<any>(result.forecast_errors).map(([m, e]) => (
                <tr key={m} className={m === 'VARUNA_FUSED' ? 'font-bold text-primary' : ''}><td>{m}</td><td className="text-right">{e.error}</td><td className="text-right">{e.abs_error}</td></tr>
              ))}</tbody>
            </table>
          )}
          {result.observation_source && <div className="text-[10px] text-on-surface-variant">Observation: {result.observation_source}</div>}
          {result.status === 'VERIFIED' && (can('skill:update') ? (
            <button disabled={busy} onClick={skill} className="mt-1 flex items-center gap-1 px-2.5 py-1 rounded bg-secondary text-on-secondary font-bold disabled:opacity-40">
              <Database className="w-3 h-3" /> Update skill memory
            </button>
          ) : (
            <div className="text-[10px] text-on-surface-variant">Stored. A model analyst folds verified errors into skill memory (or an approved RECALIBRATE_SKILL proposal).</div>
          ))}
          {skillMsg && <div className="text-[10px]">{skillMsg}</div>}
        </div>
      )}
    </div>
  );
};

export const PipelineTrace: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { summary, refreshData, isLoading, setActiveRoute } = useVaruna();
  const [open, setOpen] = useState<StageTraceItem | null>(null);
  const trace = summary.stage_trace || [];
  const total = trace.reduce((a, t) => a + (t.duration_ms || 0), 0);

  return (
    <div className={`w-full bg-surface-container-low p-3 rounded-xl border border-outline-variant/30 shadow-xs ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <span className="text-xs font-bold text-on-surface uppercase tracking-wider">Pipeline stage trace</span>
        <div className="flex items-center gap-2 font-mono text-[10px] text-on-surface-variant">
          {trace.length > 0 && <span>{trace.filter(t => t.status === 'PASS' || t.status === 'WARN').length}/{trace.length} run · {total.toFixed(1)} ms · {fmtTime(summary.computed_at)}</span>}
          <button onClick={() => refreshData()} disabled={isLoading}
            className="flex items-center gap-1 px-2 py-0.5 rounded border border-outline-variant/40 hover:bg-surface-container text-on-surface disabled:opacity-50"
            title="Run the pipeline again with the current inputs">
            <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} /> Re-run
          </button>
        </div>
      </div>

      {trace.length === 0 ? (
        <div className="text-xs text-on-surface-variant font-mono">Stage trace unavailable (offline demo). Connect the backend to see each stage's inputs, outputs and timing.</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-1.5">
          {trace.map(t => (
            <button
              key={t.key}
              onClick={() => setOpen(t)}
              title={t.notes || t.name}
              className={`flex flex-col items-start p-1.5 rounded border text-[10px] font-mono text-left hover:ring-1 hover:ring-primary/50 focus:outline-none focus:ring-2 focus:ring-primary ${statusStyle(t.status)}`}
            >
              <span className="flex items-center gap-1 font-bold"><StatusIcon s={t.status} />{t.stage}. {t.key.replace('_', ' ')}</span>
              <span className="opacity-80">{t.status === 'PENDING' ? 'awaiting obs · act' : `${t.status} · ${t.duration_ms.toFixed(1)} ms`}</span>
            </button>
          ))}
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-[120] flex justify-end bg-black/30" onClick={() => setOpen(null)}>
          <aside onClick={e => e.stopPropagation()} className="h-full w-full max-w-md bg-surface-container-lowest border-l border-outline-variant/40 shadow-2xl overflow-y-auto p-4 font-mono text-xs text-on-surface">
            <div className="flex items-start justify-between gap-2 mb-3">
              <div>
                <div className="text-[10px] text-on-surface-variant">Stage {open.stage} of 14</div>
                <div className="text-sm font-bold">{open.name}</div>
                <span className={`inline-flex items-center gap-1 mt-1 px-1.5 py-0.5 rounded border text-[10px] ${statusStyle(open.status)}`}><StatusIcon s={open.status} />{open.status}</span>
                <span className="ml-2 text-[10px] text-on-surface-variant">{open.duration_ms.toFixed(2)} ms</span>
              </div>
              <button onClick={() => setOpen(null)} className="p-1 rounded hover:bg-surface-container" aria-label="Close"><X className="w-4 h-4" /></button>
            </div>
            {open.notes && <p className="mb-3 text-on-surface-variant leading-relaxed">{open.notes}</p>}
            <div className="mb-3"><div className="text-[10px] font-bold uppercase text-on-surface-variant mb-1">Inputs</div><KV data={open.inputs} /></div>
            <div className="mb-3"><div className="text-[10px] font-bold uppercase text-on-surface-variant mb-1">Outputs</div><KV data={open.outputs} /></div>
            {open.key === 'VERIFY' && open.status === 'PENDING' && (
              <div className="mb-3 p-2 rounded border border-sky-500/30"><div className="text-[10px] font-bold uppercase mb-1 flex items-center gap-1"><Play className="w-3 h-3" />Verify this forecast</div><VerifyPanel /></div>
            )}
            {STAGE_ROUTE[open.key] && (
              <button onClick={() => { setActiveRoute(STAGE_ROUTE[open.key].route); setOpen(null); }}
                className="flex items-center gap-1 px-2.5 py-1 rounded border border-primary/40 text-primary font-bold hover:bg-primary/10">
                Open {STAGE_ROUTE[open.key].label} <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </aside>
        </div>
      )}
    </div>
  );
};
