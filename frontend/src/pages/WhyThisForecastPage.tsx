import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { Traceable, TraceBody } from '../components/shared/Traceable';
import { SourceModeBadge } from '../components/shared/SourceModeBadge';
import { modelInfo, fmtTime } from '../utils/models';
import { HelpCircle, AlertTriangle } from 'lucide-react';

const API_BASE: string = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';
const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';

const EVIDENCE_LABEL: Record<string, string> = {
  DATABASE_VERIFIED_HISTORY: 'verified history (this region)',
  SEEDED_PRIOR: 'seeded prior (not verified)',
  BOOTSTRAP_PRIOR: 'bootstrap prior (no history)',
  SCENARIO_PRIOR: 'synthetic scenario prior',
  VERIFIED_EMA: 'verified recent errors (EMA)',
  'PRIOR_DERIVED (0.5 x MAE)': 'derived from prior (0.5 × MAE)',
};

/** "Why this forecast?" — every statement on this page is generated from the run's lineage. */
export const WhyThisForecastPage: React.FC = () => {
  const { summary, regionId, variable } = useVaruna();
  const lin = summary.lineage || {};
  const unit = summary.unit;
  const [liveSkill, setLiveSkill] = useState<any>(null);
  const [bench, setBench] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_BASE}/verification/live-skill?region_id=${regionId}&variable=${variable}`).then(r => r.ok ? r.json() : null).then(setLiveSkill).catch(() => setLiveSkill(null));
  }, [regionId, variable]);
  useEffect(() => {
    fetch(`${API_BASE}/verification/compare`).then(r => r.ok ? r.json() : null).then(setBench).catch(() => setBench(null));
  }, []);

  const weights = [...(summary.weights || [])].sort((a, b) => b.weight - a.weight);
  const dominant = weights[0];
  const explanation: any = summary.explanation || {};
  const factors = explanation.factors || {};
  const leadKey = String(summary.lead_hours);
  const live = liveSkill?.leads?.[leadKey];

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 text-on-surface">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2"><HelpCircle className="w-5 h-5" /> Why this forecast?</h1>
          <p className="text-sm text-on-surface-variant mt-1 max-w-3xl">
            The fused value, each model's weight and the confidence below are explained from the numbers the pipeline actually used.
            Hover or click any underlined number for its formula and sources.
          </p>
        </div>
        <SourceModeBadge />
      </div>

      <div className={`${card} grid grid-cols-1 md:grid-cols-4 gap-3 font-mono text-xs`}>
        <div><div className="text-[10px] text-on-surface-variant">Fused forecast</div>
          <div className="text-2xl font-bold"><Traceable field="fused_value">{summary.fused_forecast} {unit}</Traceable></div></div>
        <div><div className="text-[10px] text-on-surface-variant">Most trusted model</div>
          <div className="text-base font-bold">{dominant ? modelInfo(dominant.model_id, summary.source_meta?.[dominant.model_id]).label : '—'}</div>
          {dominant && <Traceable field="weight" model={dominant.model_id}>{(dominant.weight * 100).toFixed(1)}% weight</Traceable>}</div>
        <div><div className="text-[10px] text-on-surface-variant">Confidence</div>
          <div className="text-base font-bold"><Traceable field="confidence">{summary.uncertainty?.confidence} ({summary.uncertainty?.confidence_score?.toFixed(2)})</Traceable></div></div>
        <div><div className="text-[10px] text-on-surface-variant">Disagreement</div>
          <div className="text-base font-bold"><Traceable field="disagreement">{summary.disagreement?.disagreement_level}</Traceable></div></div>
      </div>

      {explanation.text && (
        <div className={card}>
          <div className="text-[10px] font-bold uppercase text-on-surface-variant mb-1 font-mono">Briefing (restates computed facts only)</div>
          <p className="text-sm leading-relaxed">{explanation.text}</p>
          {(factors.positive_factors?.length || factors.negative_factors?.length) ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2 text-xs">
              <ul className="list-disc pl-4 space-y-0.5">{(factors.positive_factors || []).map((f: string, i: number) => <li key={i}>{f}</li>)}</ul>
              <ul className="list-disc pl-4 space-y-0.5 text-amber-800 dark:text-amber-300">{(factors.negative_factors || []).map((f: string, i: number) => <li key={i}>{f}</li>)}</ul>
            </div>
          ) : null}
        </div>
      )}

      <div className={card}>
        <div className="font-bold text-sm mb-2">Why each model got its weight · strategy {summary.strategy}</div>
        {summary.strategy_note && <div className="text-xs text-on-surface-variant mb-2">{summary.strategy_note}</div>}
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 font-mono min-w-[720px]">
            <thead><tr className="text-left text-on-surface-variant"><th>model</th><th className="text-right">forecast</th><th className="text-right">weight</th><th className="text-right">hist. MAE</th><th>MAE evidence</th><th className="text-right">recent error</th><th>recent evidence</th><th className="text-right">bias corr.</th></tr></thead>
            <tbody>{weights.map(w => {
              const l = lin.weights?.[w.model_id];
              return (
                <tr key={w.model_id} className="border-t border-outline-variant/20">
                  <td className="py-1"><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: modelInfo(w.model_id).hex }} />{modelInfo(w.model_id, summary.source_meta?.[w.model_id]).label}</td>
                  <td className="text-right"><Traceable field="model_forecast" model={w.model_id} glyph={false}>{(summary.model_forecasts as any)?.[w.model_id] ?? '—'}</Traceable></td>
                  <td className="text-right font-bold"><Traceable field="weight" model={w.model_id} glyph={false}>{(w.weight * 100).toFixed(1)}%</Traceable></td>
                  <td className="text-right">{l?.historical_mae?.toFixed?.(2) ?? '—'}</td>
                  <td>{EVIDENCE_LABEL[l?.skill_provenance || ''] || l?.skill_provenance || '—'}</td>
                  <td className="text-right">{l?.recent_error?.toFixed?.(2) ?? '—'}</td>
                  <td>{EVIDENCE_LABEL[l?.recent_error_provenance || ''] || l?.recent_error_provenance || '—'}</td>
                  <td className="text-right">{l?.bias_correction ?? '—'}</td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
        {weights[0] && lin.weights?.[weights[0].model_id]?.formula && (
          <div className="text-[11px] font-mono text-on-surface-variant mt-2">Formula: {lin.weights[weights[0].model_id].formula}</div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={card}><TraceBody field="fused_value" /></div>
        <div className={`${card} font-mono text-xs`}>
          <div className="font-bold text-sm font-sans mb-2">Evidence behind the weights</div>
          {live && Object.keys(live).length ? (
            <>
              <div className="text-on-surface-variant mb-1">Verified against {liveSkill.reference || "observed truth"} for this region, lead {leadKey} h (updated {fmtTime(liveSkill.updated_at)}):</div>
              <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5">
                <thead><tr className="text-left text-on-surface-variant"><th>model</th><th className="text-right">MAE</th><th className="text-right">bias</th><th className="text-right">n days</th></tr></thead>
                <tbody>{Object.entries<any>(live).sort((a, b) => (a[1].MAE ?? 99) - (b[1].MAE ?? 99)).map(([m, s]) => (
                  <tr key={m} className="border-t border-outline-variant/20"><td className="py-0.5">{modelInfo(m).label}</td><td className="text-right">{s.MAE?.toFixed(2)}</td><td className="text-right">{s.BIAS?.toFixed(2)}</td><td className="text-right">{s.n}</td></tr>
                ))}</tbody>
              </table>
            </>
          ) : (
            <div className="text-on-surface-variant flex items-start gap-1"><AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-amber-600" />
              No verified history for this region and lead yet, so weights rest on priors. Run a backfill in Data sources to replace them with measured skill.</div>
          )}
          {bench?.baselines && (
            <div className="mt-3 pt-2 border-t border-outline-variant/30">
              <div className="text-on-surface-variant mb-1">Method comparison on the synthetic chronological benchmark ({bench.sample_size} unseen days — synthetic, not operational):</div>
              {['SIMPLE_AVERAGE', 'STATIC_BLEND', 'ADAPTIVE_RELIABILITY_BASELINE', 'ADAPTIVE_BLEND', 'BIAS_CORRECTED_STACKING'].map(k => bench.baselines[k] && (
                <div key={k} className="flex justify-between"><span>{k.replace(/_/g, ' ').toLowerCase()}</span><span>MAE {bench.baselines[k].mae}</span></div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className={`${card} text-xs text-on-surface-variant`}>
        <div className="font-bold text-on-surface mb-1">Limits of this explanation</div>
        <ul className="list-disc pl-4 space-y-0.5">
          <li>The weather regime is selected by the forecaster, not detected from the fields.</li>
          <li>The exceedance figure is an uncalibrated indicator, not a probability.</li>
          <li>Values are point/subdivision extractions; no spatial downscaling is applied.</li>
          {(!summary.source_mode || summary.source_mode === 'SYNTHETIC_DEMO') && <li>The model values on this run are a synthetic scenario.</li>}
        </ul>
      </div>
    </div>
  );
};
