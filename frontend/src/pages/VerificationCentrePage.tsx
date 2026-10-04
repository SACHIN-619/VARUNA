import React, { useState, useEffect } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { fetchVerificationSummary } from '../services/api';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { CheckCircle2, TrendingUp, ShieldCheck, Activity, BarChart3, Clock } from 'lucide-react';

export const VerificationCentrePage: React.FC = () => {
  const { variable } = useVaruna();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetchVerificationSummary(variable).then(res => {
      if (isMounted) {
        setData(res);
        setLoading(false);
      }
    });
    return () => { isMounted = false; };
  }, [variable]);

  // No hard-coded fallback: if the benchmark API is unreachable the table says so.
  const rawMetrics = data?.metrics || {};

  const row = (name: string, key: string, highlight = false) => {
    const m = rawMetrics?.[key];
    return m && typeof m.mae === 'number'
      ? { name, mae: m.mae, rmse: m.rmse ?? 0, bias: m.bias ?? 0, corr: m.correlation ?? 0, highlight }
      : null;
  };
  // Rows come from the backend benchmark; missing methods are skipped instead of crashing on .toFixed
  const modelMetrics = [
    row("Bias-Corrected Stacking", 'BIAS_CORRECTED_STACKING', true),
    row("VARUNA (Adaptive ML)", 'VARUNA_ADAPTIVE_ML', true),
    row("Adaptive Reliability (Heuristic)", 'ADAPTIVE_RELIABILITY'),
    row("Static Weighted Blend", 'STATIC_BLEND'),
    row("Simple Multi-Model Average", 'SIMPLE_AVERAGE'),
    row("NCUM 12km (Raw NWP)", 'NCUM_RAW'),
    row("WRF 3km (Raw NWP)", 'WRF_RAW'),
    row("AI Weather Model (Raw)", 'AI_WEATHER_RAW'),
    row("NOAA GFS 25km (Raw NWP)", 'GFS_RAW'),
  ].filter(Boolean) as Array<{ name: string; mae: number; rmse: number; bias: number; corr: number; highlight?: boolean }>;

  const simpleMae = modelMetrics.find(m => m.name === 'Simple Multi-Model Average')?.mae;


  const { regionId, summary } = useVaruna();
  const [liveSkill, setLiveSkill] = useState<any>(null);
  const [records, setRecords] = useState<any[]>([]);
  useEffect(() => {
    const base = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';
    fetch(`${base}/verification/live-skill?region_id=${regionId}&variable=${variable}`).then(r => r.ok ? r.json() : null).then(setLiveSkill).catch(() => setLiveSkill(null));
    fetch(`${base}/verification/records?region_id=${regionId}&variable=${variable}&limit=30`).then(r => r.ok ? r.json() : []).then(setRecords).catch(() => setRecords([]));
  }, [regionId, variable, summary.run_id]);

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-bold uppercase tracking-wider">
              Continuous Verification Loop
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="CONTROLLED SYNTHETIC BENCHMARK" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            FORECAST VERIFICATION CENTRE
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Leak-free chronological benchmark on a controlled synthetic dataset ({data?.test_days ?? '—'} held-out test days, {data?.evaluation_protocol ?? ''}). These metrics demonstrate pipeline behaviour and do not represent operational meteorological performance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400 border border-emerald-600 font-mono text-xs font-bold">
            {data ? `ML ${data.skill_improvement_mae}` : 'Loading benchmark…'}
            {data?.stacking_improvement_mae != null && ` · Stacking ${data.stacking_improvement_mae > 0 ? '+' : ''}${data.stacking_improvement_mae}%`}
          </span>
        </div>
      </div>

      {/* Main Scientific Performance Metric Table */}
      <div className="p-5 rounded-2xl bg-surface border border-surface-border shadow-xl">
        <div className="flex items-center justify-between pb-3 border-b border-surface-border mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            <h2 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
              Synthetic benchmark: {data?.test_days ?? '—'} chronological held-out test days
            </h2>
          </div>
          <span className="text-xs font-mono text-on-surface-variant">
            Temporal Split (Strictly Causal; Zero Future Leakage)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-surface-border text-on-surface-variant bg-surface-deep/60">
                <th className="p-3">SYSTEM / MODEL</th>
                <th className="p-3">MAE (mm) ↓</th>
                <th className="p-3">RMSE (mm) ↓</th>
                <th className="p-3">BIAS (mm)</th>
                <th className="p-3">PEARSON r ↑</th>
                <th className="p-3">MAE SKILL vs BASELINE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {modelMetrics.map((m, idx) => (
                <tr 
                  key={idx}
                  className={`transition-colors ${
                    m.highlight 
                      ? 'bg-cyan-50 dark:bg-cyan-950/40 text-primary font-bold border-l-4 border-cyan-400' 
                      : 'hover:bg-surface-card text-on-surface-variant'
                  }`}
                >
                  <td className="p-3 font-headline flex items-center gap-2">
                    {m.highlight && <CheckCircle2 className="w-4 h-4 text-primary" />}
                    <span>{m.name}</span>
                  </td>
                  <td className="p-3 font-bold text-on-surface">{m.mae.toFixed(2)}</td>
                  <td className="p-3">{m.rmse.toFixed(2)}</td>
                  <td className={`p-3 font-semibold ${m.bias > 1.0 ? 'text-amber-600 dark:text-amber-400' : 'text-on-surface-variant'}`}>
                    {m.bias > 0 ? `+${m.bias.toFixed(2)}` : m.bias.toFixed(2)}
                  </td>
                  <td className="p-3">{m.corr.toFixed(3)}</td>
                  <td className="p-3">
                    {simpleMae && m.name !== 'Simple Multi-Model Average' ? (
                      <span className={`font-extrabold ${simpleMae - m.mae > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                        {((simpleMae - m.mae) / simpleMae * 100) > 0 ? '+' : ''}{((simpleMae - m.mae) / simpleMae * 100).toFixed(1)}%
                      </span>
                    ) : m.name === 'Simple Multi-Model Average' ? (
                      <span className="text-on-surface-variant">0.0% (Baseline)</span>
                    ) : (
                      <span className="text-on-surface-variant">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Closed-Loop Verification to Skill Memory Diagram */}
      <div className="p-6 rounded-2xl bg-surface-deep border border-surface-border flex flex-col gap-4">
        <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span>Closed loop: verify → skill memory → next weights</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-surface border border-surface-border">
            <span className="text-[10px] text-primary font-bold block mb-1">STEP 01</span>
            <div className="font-bold text-on-surface text-sm mb-1">Forecast Issued</div>
            <p className="text-on-surface-variant text-[11px] leading-relaxed">
              VARUNA generates fused forecast with normalized trust vector (w_i).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-surface border border-surface-border">
            <span className="text-[10px] text-primary font-bold block mb-1">STEP 02</span>
            <div className="font-bold text-on-surface text-sm mb-1">Observation Arrives</div>
            <p className="text-on-surface-variant text-[11px] leading-relaxed">
              Observation entered (gauge / AWS), IMD gridded value (~2 days later) or ERA5 fallback (stage 14 in the trace).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-surface border border-surface-border">
            <span className="text-[10px] text-primary font-bold block mb-1">STEP 03</span>
            <div className="font-bold text-on-surface text-sm mb-1">Residual Error Computed</div>
            <p className="text-on-surface-variant text-[11px] leading-relaxed">
              e_i = |y_obs - y_pred,i| computed across all individual models and blend.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-surface border border-emerald-500/40 shadow-glow-cyan/10">
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold block mb-1">STEP 04</span>
            <div className="font-bold text-on-surface text-sm mb-1">Skill memory update</div>
            <p className="text-on-surface-variant text-[11px] leading-relaxed">
              Skill memory: MAE = mean of verified |errors|; recent error = EMA (α = 0.3) of the last 10. Next run's weights use both.
            </p>
          </div>
        </div>
      </div>

      {/* Real verification for the selected region */}
      <div className="p-5 rounded-2xl bg-surface border border-surface-border font-mono text-xs">
        <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider mb-2">Verified skill · {regionId} · {variable} ({liveSkill?.reference || "IMD gridded / ERA5"})</h3>
        {liveSkill && Object.keys(liveSkill.leads || {}).length ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries<any>(liveSkill.leads).map(([lead, models]) => (
              <table key={lead} className="w-full text-[11px]">
                <caption className="text-left font-bold mb-1">Lead {lead} h</caption>
                <thead><tr className="text-left text-on-surface-variant"><th>model</th><th className="text-right">MAE</th><th className="text-right">RMSE</th><th className="text-right">bias</th><th className="text-right">n</th></tr></thead>
                <tbody>{Object.entries<any>(models).sort((a, b) => (a[1].MAE ?? 99) - (b[1].MAE ?? 99)).map(([m, s]) => (
                  <tr key={m} className="border-t border-surface-border"><td className="py-0.5">{m}</td><td className="text-right">{s.MAE?.toFixed(2)}</td><td className="text-right">{s.RMSE?.toFixed(2)}</td><td className="text-right">{s.BIAS?.toFixed(2)}</td><td className="text-right">{s.n}</td></tr>
                ))}</tbody>
              </table>
            ))}
          </div>
        ) : (
          <div className="text-on-surface-variant">No verified history for this region yet. Operations / analysts: Data sources → Run backfill (previous model runs vs IMD gridded observations).</div>
        )}
      </div>

      <div className="p-5 rounded-2xl bg-surface border border-surface-border font-mono text-xs">
        <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider mb-2">Latest verification records</h3>
        {records.length === 0 ? <div className="text-on-surface-variant">None stored yet. Open stage 14 in the control-room trace to verify the current run.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 min-w-[600px]">
              <thead><tr className="text-left text-on-surface-variant"><th>time</th><th>model</th><th className="text-right">lead</th><th className="text-right">forecast</th><th className="text-right">observed</th><th className="text-right">|error|</th><th>window</th></tr></thead>
              <tbody>{records.map((r, i) => (
                <tr key={i} className="border-t border-surface-border"><td className="py-0.5">{(r.time || '').slice(0, 16).replace('T', ' ')}</td><td>{r.model_id}</td><td className="text-right">{r.lead_hours}</td><td className="text-right">{r.forecast}</td><td className="text-right">{r.observed}</td><td className="text-right">{r.abs_error}</td><td>{r.window}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
