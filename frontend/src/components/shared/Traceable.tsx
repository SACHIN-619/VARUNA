import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Info, X } from 'lucide-react';
import { useVaruna } from '../../context/VarunaContext';
import { fmtTime, modelInfo, PROVENANCE_LABEL } from '../../utils/models';

export type TraceField =
  | 'fused_value' | 'simple_average' | 'static_blend' | 'confidence' | 'probability'
  | 'uncertainty_margin' | 'disagreement' | 'extreme_signal' | 'weight' | 'model_forecast';

interface TraceableProps {
  field: TraceField;
  model?: string;
  children: React.ReactNode;
  className?: string;
  /** Show the small info glyph after the value (default true). */
  glyph?: boolean;
}

const fmt = (v: any): string => {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(Math.abs(v) < 1 ? 3 : 2);
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
};

const Row: React.FC<{ k: string; v: any }> = ({ k, v }) => (
  <div className="flex justify-between gap-3 py-0.5 border-b border-outline-variant/15 last:border-0">
    <span className="text-on-surface-variant shrink-0">{k}</span>
    <span className="text-on-surface text-right break-all">{fmt(v)}</span>
  </div>
);

/** The explanation body for a number: what it is, the formula, the inputs and where each input came from. */
export const TraceBody: React.FC<{ field: TraceField; model?: string }> = ({ field, model }) => {
  const { summary } = useVaruna();
  const lin = summary.lineage || {};
  const meta = summary.source_meta || {};
  const unit = summary.unit;
  const mode = summary.source_mode || (summary.data_mode === 'DEMO' ? 'OFFLINE_DEMO' : 'SYNTHETIC_DEMO');

  const sourceLine = (m: string) => {
    const sm = meta[m] || lin.model_forecasts?.[m] || {};
    return (
      <div key={m} className="py-1 border-b border-outline-variant/15 last:border-0">
        <div className="flex justify-between gap-2">
          <span className="font-bold text-on-surface">{modelInfo(m, sm).label}</span>
          <span className="text-on-surface">{fmt(summary.model_forecasts?.[m as keyof typeof summary.model_forecasts])} {unit}</span>
        </div>
        <div className="text-[10px] text-on-surface-variant">
          {PROVENANCE_LABEL[sm.provenance || ''] || sm.provenance || 'Synthetic demo scenario'}
          {sm.source ? ` · ${sm.source}` : ''}
          {sm.issue_time ? ` · issued ${fmtTime(sm.issue_time)}` : ''}
          {sm.fetched_at ? ` · received ${fmtTime(sm.fetched_at)}` : ''}
        </div>
      </div>
    );
  };

  let title = '';
  let body: React.ReactNode = null;
  switch (field) {
    case 'fused_value': {
      const f = lin.fused_value;
      title = 'Fused forecast';
      body = f ? (
        <>
          <div className="mb-1 text-primary">{f.formula} = <strong>{fmt(f.value)} {unit}</strong></div>
          <table className="w-full text-[10px]">
            <thead><tr className="text-on-surface-variant"><th className="text-left">model</th><th className="text-right">w</th><th className="text-right">F</th>{f.bias_correction && <th className="text-right">bias</th>}<th className="text-right">w·F</th></tr></thead>
            <tbody>
              {f.terms.map(t => (
                <tr key={t.model} className={t.weight > 0 ? '' : 'opacity-50'}>
                  <td>{modelInfo(t.model, meta[t.model]).label}</td>
                  <td className="text-right">{t.weight.toFixed(3)}</td>
                  <td className="text-right">{fmt(t.value)}</td>
                  {f.bias_correction && <td className="text-right">{fmt(f.bias_correction[t.model])}</td>}
                  <td className="text-right">{fmt(t.product)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-1 text-[10px] text-on-surface-variant">Strategy: {summary.strategy}{summary.strategy_note ? ` — ${summary.strategy_note}` : ''}</div>
        </>
      ) : null;
      break;
    }
    case 'simple_average':
    case 'static_blend': {
      const f = lin[field];
      title = field === 'simple_average' ? 'Simple average (baseline)' : 'Static blend (baseline)';
      body = f ? <><Row k="value" v={`${fmt(f.value)} ${unit}`} /><Row k="formula" v={f.formula} /></> : null;
      break;
    }
    case 'confidence': {
      const c = lin.confidence || {};
      title = 'Confidence';
      body = <>
        <Row k="score" v={c.value} /><Row k="grade" v={c.level} />
        <Row k="formula" v={c.confidence_formula} />
        <Row k="disagreement score" v={c.disagreement_score} /><Row k="missing ratio" v={c.missing_ratio} />
        <Row k="lead decay" v={c.lead_decay} /><Row k="active models" v={`${c.active_count ?? '—'} / ${c.total_expected ?? '—'}`} />
      </>;
      break;
    }
    case 'probability': {
      const p = lin.probability || {};
      title = 'Exceedance indicator (uncalibrated)';
      body = <>
        <Row k="value (%)" v={p.value} /><Row k="threshold" v={`${fmt(p.threshold)} ${unit}`} />
        <Row k="σ" v={p.sigma} /><Row k="formula" v={p.formula} />
        <div className="mt-1 text-[10px] text-amber-700 dark:text-amber-400">Not a calibrated probability: no reliability diagram has been fitted yet.</div>
      </>;
      break;
    }
    case 'uncertainty_margin': {
      const u = lin.uncertainty_margin || {};
      title = 'Uncertainty margin';
      body = <><Row k="± value" v={`${fmt(u.value)} ${unit}`} /><Row k="formula" v={u.formula} /></>;
      break;
    }
    case 'disagreement': {
      const d = lin.disagreement || {};
      title = 'Model disagreement';
      body = <>
        <Row k="score" v={d.value} /><Row k="level" v={d.level} /><Row k="std dev" v={d.std_dev} />
        <Row k="range" v={d.range} /><Row k="weighted spread" v={d.weighted_spread} /><Row k="formula" v={d.formula} />
      </>;
      break;
    }
    case 'extreme_signal': {
      const e = lin.extreme_signal || {};
      title = 'Extreme signal';
      body = <><Row k="level" v={e.alert_level} /><Row k="category" v={e.category} /><Row k="above threshold by" v={e.threshold_exceeded} /><Row k="rule" v={e.rule} /></>;
      break;
    }
    case 'weight': {
      const w = model ? lin.weights?.[model] : undefined;
      title = `Trust weight · ${model ? modelInfo(model, meta[model]).label : ''}`;
      body = w ? <>
        <Row k="weight" v={w.value} /><Row k="strategy" v={w.strategy} /><Row k="formula" v={w.formula} />
        <Row k="historical MAE" v={w.historical_mae} /><Row k="MAE evidence" v={w.skill_provenance} />
        <Row k="recent error" v={w.recent_error} /><Row k="recent-error evidence" v={w.recent_error_provenance} />
        {w.predicted_error != null && <Row k="predicted error (ML)" v={w.predicted_error} />}
        {w.bias_correction != null && <Row k="bias correction" v={w.bias_correction} />}
      </> : null;
      break;
    }
    case 'model_forecast': {
      title = 'Model forecast';
      body = model ? sourceLine(model) : null;
      break;
    }
  }

  return (
    <div className="font-mono text-[11px] leading-relaxed">
      <div className="font-bold text-on-surface mb-1">{title}</div>
      {body || <div className="text-on-surface-variant">No lineage for this value (offline demo or older backend).</div>}
      {(field === 'fused_value' || field === 'disagreement') && (
        <div className="mt-2 pt-1 border-t border-outline-variant/30">
          <div className="text-[10px] font-bold text-on-surface-variant uppercase mb-0.5">Inputs & sources</div>
          {Object.keys(summary.model_forecasts || {}).map(sourceLine)}
        </div>
      )}
      <div className="mt-2 text-[10px] text-on-surface-variant">
        Data: {mode === 'LIVE_PUBLIC_MODELS' ? 'global public model forecasts' : mode === 'INDIA_OPERATIONAL' ? 'NCMRWF / IMD feeds' : mode === 'INDIA_OPERATIONAL_PLUS_GLOBAL' ? 'NCMRWF / IMD feeds + global models' : mode === 'STORED_DATA' ? 'stored / uploaded data' : 'synthetic demo scenario'}
        {lin.computed_at ? ` · computed ${fmtTime(lin.computed_at)}` : ''}{summary.run_id ? ` · run ${summary.run_id}` : ''}
      </div>
    </div>
  );
};

/**
 * Wrap any displayed number: hover shows how it was computed, click pins the explanation.
 * Works for keyboard users (focus/Enter) and on touch screens (tap).
 */
export const Traceable: React.FC<TraceableProps> = ({ field, model, children, className = '', glyph = true }) => {
  const [hover, setHover] = useState(false);
  const [pinned, setPinned] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const open = hover || pinned;

  useEffect(() => {
    if (!open || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const width = Math.min(360, window.innerWidth - 16);
    const left = Math.max(8, Math.min(r.left, window.innerWidth - width - 8));
    const below = r.bottom + 8;
    const top = below + 320 > window.innerHeight && r.top > 340 ? Math.max(8, r.top - 8 - 320) : below;
    setPos({ top, left });
  }, [open]);

  useEffect(() => {
    if (!pinned) return;
    const close = (e: KeyboardEvent) => e.key === 'Escape' && setPinned(false);
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [pinned]);

  return (
    <>
      <span
        ref={ref}
        role="button"
        tabIndex={0}
        aria-label="Show how this number was computed"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={(e) => { e.stopPropagation(); setPinned(p => !p); }}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setPinned(p => !p); } }}
        className={`cursor-help underline decoration-dotted decoration-primary/40 underline-offset-4 hover:decoration-primary inline-flex items-baseline gap-0.5 ${className}`}
      >
        {children}
        {glyph && <Info className="w-3 h-3 text-primary/60 self-center shrink-0" aria-hidden />}
      </span>
      {open && createPortal(
        <div
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          style={{ top: pos.top, left: pos.left, width: Math.min(360, window.innerWidth - 16) }}
          className="fixed z-[200] max-h-[320px] overflow-y-auto rounded-lg border border-outline-variant/40 bg-surface-container-lowest p-3 shadow-2xl text-on-surface"
        >
          {pinned && (
            <button onClick={() => setPinned(false)} className="absolute top-1.5 right-1.5 p-0.5 rounded hover:bg-surface-container" aria-label="Close">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <TraceBody field={field} model={model} />
          {!pinned && <div className="mt-1 text-[9px] text-on-surface-variant">Click to pin</div>}
        </div>,
        document.body
      )}
    </>
  );
};
