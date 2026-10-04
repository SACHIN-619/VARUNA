import React, { useEffect, useState } from 'react';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { FlaskConical, CheckCircle2, TrendingUp, ShieldCheck, Database, Calendar } from 'lucide-react';

type Exp = { id: string; strategy: string; type: string; mae: number; rmse: number; gain: string; color: string; description: string; highlight?: boolean };

const DESCRIPTIONS: Record<string, [string, string, string]> = {
  SIMPLE_AVERAGE: ["Simple Multi-Model Average", "Uniform Baseline", "Equal weighting w_i = 0.25 across all 4 models without regime conditioning."],
  STATIC_BLEND: ["Static Weighted Blend", "Linear Climatological Baseline", "Fixed weights (NCUM 0.40, WRF 0.30, GFS 0.20, AI 0.10)."],
  ADAPTIVE_RELIABILITY_BASELINE: ["Adaptive Reliability (Heuristic)", "Physical Heuristic Baseline", "Inverse-MAE x recent-error x regime-vulnerability weights."],
  ADAPTIVE_ML_META_MODEL: ["Adaptive ML Meta-Model", "Learned Supervised Softmax", "GBDT error estimation with temperature-scaled softmax simplex weighting."],
  BIAS_CORRECTED_STACKING: ["Bias-Corrected Stacking", "Conditional Bias Removal + NNLS", "Removes each model's regime/lead-conditional bias, then learns convex weights (shrunk toward global)."],
};

export const ExperimentsPage: React.FC = () => {
  // All numbers come from the backend benchmark (`/api/verification/compare`); nothing is hard-coded.
  const [bench, setBench] = useState<any>(null);
  useEffect(() => {
    fetch(`${((import.meta as any).env?.VITE_API_BASE as string) || '/api'}/verification/compare`)
      .then(r => (r.ok ? r.json() : null)).then(setBench).catch(() => setBench(null));
  }, []);
  const rows: any[] = bench?.methods || [];
  const simple = rows.find(r => r.method === 'SIMPLE_AVERAGE');
  const best = bench?.best_method;
  const experiments: Exp[] = Object.keys(DESCRIPTIONS).map((k, i) => {
    const r = rows.find(x => x.method === k);
    if (!r) return null;
    const g = simple && k !== 'SIMPLE_AVERAGE' ? ((simple.mae - r.mae) / simple.mae) * 100 : 0;
    return {
      id: `EXP-00${i + 1}`,
      strategy: DESCRIPTIONS[k][0],
      type: DESCRIPTIONS[k][1],
      description: DESCRIPTIONS[k][2],
      mae: r.mae, rmse: r.rmse,
      gain: k === 'SIMPLE_AVERAGE' ? '0.0% (Baseline)' : `${g > 0 ? '+' : ''}${g.toFixed(1)}% MAE`,
      highlight: k === best,
      color: k === best ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-950/30 text-primary' : 'border-outline-variant bg-surface-deep text-on-surface',
    };
  }).filter(Boolean) as Exp[];
  const bestRow = rows.find(r => r.method === best);
  const bestGain = simple && bestRow ? ((simple.mae - bestRow.mae) / simple.mae) * 100 : null;

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider">
              Research & Scientific Benchmark Lab
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="CONTROLLED SYNTHETIC BENCHMARK" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            SCIENTIFIC EXPERIMENT BENCHMARKS
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Rigorous chronological held-out validation comparing VARUNA's Adaptive ML Meta-Model against baseline blending strategies.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400 border border-emerald-600 font-mono text-xs font-bold">
            {bestGain != null ? `Best: ${DESCRIPTIONS[best]?.[0] ?? best} ${bestGain > 0 ? '+' : ''}${bestGain.toFixed(1)}% MAE vs simple average` : 'Loading benchmark…'}
          </span>
        </div>
      </div>

      {/* Dataset & Protocol Metadata Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface border border-surface-border font-mono text-xs space-y-1">
          <div className="flex items-center gap-2 text-on-surface-variant">
            <Database className="w-4 h-4 text-primary" />
            <span>Dataset Provenance</span>
          </div>
          <div className="font-bold text-on-surface text-sm">Controlled Synthetic Benchmark</div>
          <div className="text-[11px] text-on-surface-variant">IMDAA 12km & AWS Grid Emulation</div>
        </div>

        <div className="p-4 rounded-xl bg-surface border border-surface-border font-mono text-xs space-y-1">
          <div className="flex items-center gap-2 text-on-surface-variant">
            <Calendar className="w-4 h-4 text-primary" />
            <span>Causal Temporal Split</span>
          </div>
          <div className="font-bold text-on-surface text-sm">60% train · 15% val · {bench?.sample_size ?? '—'} test days</div>
          <div className="text-[11px] text-on-surface-variant">Chronological (Zero Future Leakage)</div>
        </div>

        <div className="p-4 rounded-xl bg-surface border border-surface-border font-mono text-xs space-y-1">
          <div className="flex items-center gap-2 text-on-surface-variant">
            <TrendingUp className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Measured MAE Skill</span>
          </div>
          <div className="font-bold text-emerald-600 dark:text-emerald-400 text-sm">{bestGain != null ? `${bestGain > 0 ? '+' : ''}${bestGain.toFixed(1)}% MAE Reduction` : '—'}</div>
          <div className="text-[11px] text-on-surface-variant">{simple && bestRow ? `${simple.mae.toFixed(2)} mm → ${bestRow.mae.toFixed(2)} mm` : ''}</div>
        </div>

        <div className="p-4 rounded-xl bg-surface border border-surface-border font-mono text-xs space-y-1">
          <div className="flex items-center gap-2 text-on-surface-variant">
            <ShieldCheck className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <span>Mathematical Proof</span>
          </div>
          <div className="font-bold text-on-surface text-sm">Strict Simplex (Σw_i = 1)</div>
          <div className="text-[11px] text-on-surface-variant">Non-negative Softmax Convex Hull</div>
        </div>
      </div>

      {/* Comparison Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        {experiments.length === 0 && <div className="col-span-full text-xs font-mono text-on-surface-variant">Benchmark unavailable (backend offline).</div>}
        {experiments.map((exp) => (
          <div key={exp.id} className={`p-5 rounded-2xl border flex flex-col justify-between ${exp.color}`}>
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-surface-border mb-3">
                <span className="font-headline font-bold text-sm text-on-surface">{exp.id}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-surface-border text-on-surface-variant">
                  {exp.type}
                </span>
              </div>

              <h3 className="font-headline font-extrabold text-base text-on-surface">{exp.strategy}</h3>
              <p className="text-xs text-on-surface-variant font-sans mt-2 leading-relaxed">{exp.description}</p>

              <div className="space-y-1.5 mt-4 font-mono text-xs border-t border-surface-border pt-3">
                <div className="flex justify-between"><span>MAE:</span> <strong className="text-on-surface">{exp.mae.toFixed(2)} mm</strong></div>
                <div className="flex justify-between"><span>RMSE:</span> <strong className="text-on-surface">{exp.rmse.toFixed(2)} mm</strong></div>
              </div>
            </div>

            <div className="pt-3 border-t border-surface-border mt-4 flex items-center justify-between font-mono text-xs">
              <span className="text-on-surface-variant">Skill vs Baseline:</span>
              <span className={exp.highlight ? 'text-emerald-600 dark:text-emerald-400 font-extrabold text-sm' : 'text-on-surface-variant font-bold'}>
                {exp.gain}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Evaluation Protocol Scientific Note */}
      <div className="p-5 rounded-xl bg-surface border border-surface-border text-xs font-mono space-y-2 text-on-surface-variant">
        <div className="text-primary font-bold flex items-center gap-2">
          <FlaskConical className="w-4 h-4" />
          <span>Evaluation Protocol Transparency Statement</span>
        </div>
        <p className="text-on-surface-variant leading-relaxed font-sans text-xs">
          For scientific transparency, this benchmark is explicitly tagged as a{' '}
          <strong className="text-on-surface">Controlled Synthetic Benchmark</strong> with a strictly chronological train / validation / test split.
          Every number on this page is computed live by the backend; gains are reported relative to simple averaging on the held-out test window only.
        </p>
      </div>
    </div>
  );
};
