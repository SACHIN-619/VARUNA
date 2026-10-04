import React from 'react';
import { useVaruna } from '../context/VarunaContext';
import { PipelineTrace } from '../components/shared/PipelineTrace';
import { Traceable } from '../components/shared/Traceable';
import { SourceModeBadge, useSourceMode } from '../components/shared/SourceModeBadge';
import { IndiaMetMap } from '../components/maps/IndiaMetMap';
import { modelInfo, fmtTime } from '../utils/models';
import { Sparkles, AlertTriangle, RotateCcw, ArrowRight, Info, Database } from 'lucide-react';
import { ModelId } from '../types';

const ALERT_STYLE: Record<string, string> = {
  RED: 'bg-rose-600 text-white',
  ORANGE: 'bg-orange-500 text-white',
  YELLOW: 'bg-yellow-400 text-slate-900',
  GREEN: 'bg-emerald-600 text-white',
  GREY: 'bg-slate-500 text-white',
};

const VAR_LABEL: Record<string, string> = { rainfall: '24 h rainfall', temperature: 'Max temperature', wind_speed: 'Max 10 m wind' };

export const ControlRoomPage: React.FC = () => {
  const {
    summary, subdivisions, regionId, variable, leadHours, weatherRegime, setActiveRoute, setIsDemoModalOpen,
    simulateModelDropout, resetFailureState, simulatedDisabledModel, weights, can,
  } = useVaruna();
  const source = useSourceMode();
  const currentSub = subdivisions.find(s => s.id === regionId) || subdivisions[0];
  const unit = summary.unit;
  const alert = (summary.extreme_guidance as any)?.alert_level || 'GREEN';

  // Spread bar: real model values on a scale from min to max of all values shown
  const entries = Object.entries(summary.model_forecasts || {}).filter(([, v]) => v !== null && v !== undefined) as [string, number][];
  const values = [...entries.map(([, v]) => v), summary.fused_forecast, summary.baselines?.simple_average].filter(v => typeof v === 'number') as number[];
  const lo = values.length ? Math.min(...values) : 0;
  const hi = values.length ? Math.max(...values) : 1;
  const pos = (v: number) => (hi === lo ? 50 : 4 + ((v - lo) / (hi - lo)) * 92);

  const sorted = [...weights].sort((a, b) => b.weight - a.weight);
  const wc: any = summary.what_changed || {};
  const shifts: Record<string, number> = wc.weight_shifts_pct_points || {};
  const verifyStage = (summary.stage_trace || []).find(t => t.key === 'VERIFY');

  return (
    <div className="flex flex-col w-full pb-10 gap-4">
      {/* Situation header */}
      <section className="w-full bg-surface-container-low px-4 lg:px-6 py-3 border-b border-outline-variant/30">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
          <div className="min-w-0">
            <h1 className="text-base font-bold text-on-surface tracking-tight">
              {currentSub?.name} · {VAR_LABEL[variable] || variable} · +{leadHours} h
            </h1>
            <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] font-mono text-on-surface-variant">
              <SourceModeBadge />
              <span>Regime: <strong className="text-on-surface">{weatherRegime.replace('_', ' ')}</strong> (selected, not auto-detected)</span>
              <span>· Strategy: <strong className="text-on-surface">{summary.strategy || '—'}</strong></span>
              {summary.issue_time && <span>· Issued {fmtTime(summary.issue_time)}</span>}
              {summary.computed_at && <span>· Computed {fmtTime(summary.computed_at)}</span>}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {source.key === 'DEMO' && can('live:fetch') && (
              <button onClick={() => setActiveRoute('live-data')} className="px-2.5 py-1 rounded border border-primary/40 text-primary text-xs font-bold flex items-center gap-1 hover:bg-primary/10">
                <Database className="w-3.5 h-3.5" /> Fetch live data
              </button>
            )}
            <button onClick={() => setIsDemoModalOpen(true)} className="px-2.5 py-1 rounded bg-primary text-on-primary text-xs font-bold flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> Walkthrough
            </button>
          </div>
        </div>
        {(source.key === 'DEMO' || source.key === 'OFFLINE') && (
          <div className="mt-2 flex items-start gap-1.5 text-[11px] text-amber-800 dark:text-amber-300">
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" /> <span>{source.detail}</span>
          </div>
        )}
        {summary.strategy_note && (
          <div className="mt-1 text-[11px] text-on-surface-variant">Strategy fallback: {summary.strategy_note}</div>
        )}
      </section>

      <div className="px-4 lg:px-6"><PipelineTrace /></div>

      <div className="px-4 lg:px-6 grid grid-cols-1 xl:grid-cols-12 gap-5">
        {/* Fused forecast */}
        <div className="xl:col-span-5 flex flex-col gap-4">
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-sm border border-outline-variant/30 flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-wider font-semibold text-on-surface-variant">VARUNA fused forecast</div>
                <div className="text-xs text-on-surface-variant">{VAR_LABEL[variable]} · valid +{leadHours} h · {currentSub?.name}</div>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${ALERT_STYLE[alert] || ALERT_STYLE.GREY}`}>
                <Traceable field="extreme_signal" glyph={false}>{alert}</Traceable>
              </span>
            </div>

            <div className="flex items-baseline gap-2">
              <span className="text-5xl md:text-6xl font-extrabold text-on-surface tracking-tighter font-mono">
                <Traceable field="fused_value" glyph={false}>{summary.fused_forecast ?? '—'}</Traceable>
              </span>
              <span className="text-2xl font-bold text-primary">{unit}</span>
              <span className="text-xs font-mono text-on-surface-variant">
                ± <Traceable field="uncertainty_margin" glyph={false}>{summary.uncertainty?.uncertainty_margin?.toFixed(1) ?? '—'}</Traceable>
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs font-mono">
              <div className="p-2 rounded bg-surface-container-low">
                <div className="text-[10px] text-on-surface-variant">Confidence</div>
                <Traceable field="confidence" className="font-bold text-on-surface">
                  {summary.uncertainty?.confidence} ({summary.uncertainty?.confidence_score?.toFixed(2)})
                </Traceable>
              </div>
              <div className="p-2 rounded bg-surface-container-low">
                <div className="text-[10px] text-on-surface-variant">Simple average</div>
                <Traceable field="simple_average" className="font-bold text-on-surface">{summary.baselines?.simple_average ?? '—'}</Traceable>
              </div>
              <div className="p-2 rounded bg-surface-container-low">
                <div className="text-[10px] text-on-surface-variant">Static blend</div>
                <Traceable field="static_blend" className="font-bold text-on-surface">{summary.baselines?.static_blend ?? '—'}</Traceable>
              </div>
            </div>

            {/* Spread of the actual values */}
            {entries.length > 0 && (
              <div className="pt-1">
                <div className="flex justify-between text-[10px] font-mono text-on-surface-variant mb-1">
                  <span>{lo.toFixed(1)} {unit}</span><span>model spread</span><span>{hi.toFixed(1)} {unit}</span>
                </div>
                <div className="relative h-8 rounded bg-surface-container-high">
                  {entries.map(([m, v]) => (
                    <div key={m} className="absolute top-1 -translate-x-1/2 flex flex-col items-center" style={{ left: `${pos(v)}%` }} title={`${modelInfo(m, summary.source_meta?.[m]).label}: ${v} ${unit}`}>
                      <span className="w-1.5 h-4 rounded-sm" style={{ background: modelInfo(m).hex }} />
                    </div>
                  ))}
                  {typeof summary.fused_forecast === 'number' && (
                    <div className="absolute -top-0.5 -translate-x-1/2 w-1 h-9 bg-on-surface rounded" style={{ left: `${pos(summary.fused_forecast)}%` }} title={`Fused: ${summary.fused_forecast} ${unit}`} />
                  )}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-[10px] font-mono text-on-surface-variant">
                  {entries.map(([m]) => (
                    <span key={m} className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm" style={{ background: modelInfo(m).hex }} />{modelInfo(m, summary.source_meta?.[m]).label}</span>
                  ))}
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-on-surface" />fused</span>
                </div>
              </div>
            )}
          </div>

          {/* Trust matrix — generated from the actual model set */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-outline-variant/30 flex flex-col gap-2">
            <div className="flex items-center justify-between pb-1 border-b border-outline-variant/30">
              <h3 className="text-sm font-bold text-on-surface">Model trust weights</h3>
              <span className="text-[10px] font-mono text-on-surface-variant">{weights.filter(w => w.weight > 0).length} of {weights.length} active · Σ = 1</span>
            </div>
            {sorted.map(w => {
              const info = modelInfo(w.model_id, summary.source_meta?.[w.model_id]);
              const pct = w.weight * 100;
              const raw = summary.model_forecasts?.[w.model_id as ModelId];
              const shift = shifts[w.model_id];
              return (
                <div key={w.model_id} className="p-2 rounded bg-surface-container-low">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <div className="min-w-0">
                      <div className="font-semibold text-on-surface flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full shrink-0" style={{ background: info.hex }} />{info.label}
                        {w.status !== 'ACTIVE' && <span className="text-[10px] text-error font-mono">{w.status}</span>}
                      </div>
                      <div className="text-[10px] text-on-surface-variant truncate">{info.role}</div>
                    </div>
                    <div className="text-right font-mono shrink-0">
                      <Traceable field="weight" model={w.model_id} className="font-bold text-primary" glyph={false}>{pct.toFixed(1)}%</Traceable>
                      <div className="text-[10px] text-on-surface-variant">
                        <Traceable field="model_forecast" model={w.model_id} glyph={false}>{raw ?? '—'} {unit}</Traceable>
                        {typeof shift === 'number' && Math.abs(shift) >= 0.5 && (
                          <span className={shift > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}> {shift > 0 ? '+' : ''}{shift.toFixed(1)} pts</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-surface-container-high overflow-hidden">
                    <div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${pct}%`, background: info.hex }} />
                  </div>
                </div>
              );
            })}
            <div className="pt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
              <span className="text-on-surface-variant">What-if dropout:</span>
              {sorted.slice(0, 3).map(w => (
                <button key={w.model_id} onClick={() => simulateModelDropout(w.model_id as ModelId)}
                  className={`px-2 py-0.5 rounded border text-[10px] font-mono ${simulatedDisabledModel === w.model_id ? 'border-error text-error' : 'border-outline-variant/40 text-on-surface hover:bg-surface-container'}`}>
                  drop {modelInfo(w.model_id).label.split(' ')[0]}
                </button>
              ))}
              {simulatedDisabledModel && (
                <button onClick={resetFailureState} className="px-2 py-0.5 rounded border border-primary/40 text-primary text-[10px] font-mono flex items-center gap-1">
                  <RotateCcw className="w-3 h-3" /> reset
                </button>
              )}
            </div>
            {simulatedDisabledModel && (
              <div className="text-[10px] text-on-surface-variant">Simulation only: {simulatedDisabledModel} removed for this view; weights re-normalised by the backend. Not stored, no notification.</div>
            )}
          </div>
        </div>

        {/* Map */}
        <div className="xl:col-span-7 flex flex-col gap-2">
          <IndiaMetMap heightClass="h-[520px]" />
          <div className="text-[10px] font-mono text-on-surface-variant flex items-start gap-1">
            <Info className="w-3 h-3 mt-0.5 shrink-0" />
            Subdivision colours are an illustrative synthetic trust field; the numbers in the left panel are the computed forecast for the selected region.
          </div>
        </div>
      </div>

      {/* Bottom cards: all computed */}
      <section className="px-4 lg:px-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30">
          <div className="text-xs font-bold text-on-surface uppercase">Model disagreement</div>
          <div className="text-2xl font-bold font-mono text-on-surface mt-1">
            <Traceable field="disagreement">{summary.disagreement?.disagreement_level}</Traceable>
          </div>
          <div className="text-[11px] font-mono text-on-surface-variant mt-1">
            std {summary.disagreement?.forecast_spread?.toFixed?.(1) ?? '—'} {unit} · range {summary.disagreement?.range?.toFixed?.(1) ?? '—'} {unit}
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-on-surface uppercase">Change vs previous</span>
            <button onClick={() => setActiveRoute('what-changed')} className="text-[10px] text-primary flex items-center gap-0.5">details <ArrowRight className="w-3 h-3" /></button>
          </div>
          {typeof wc.fused_delta === 'number' ? (
            <>
              <div className={`text-2xl font-bold font-mono mt-1 ${wc.fused_delta > 0 ? 'text-rose-600 dark:text-rose-400' : wc.fused_delta < 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-on-surface'}`}>
                {wc.fused_delta > 0 ? '+' : ''}{wc.fused_delta.toFixed(1)} {unit}
              </div>
              <div className="text-[11px] font-mono text-on-surface-variant mt-1">
                {wc.previous_value} → {wc.current_value} {unit} · {(wc.comparison_basis || '').replace(/_/g, ' ').toLowerCase()}
              </div>
            </>
          ) : <div className="text-[11px] text-on-surface-variant mt-1">{wc.summary || 'No previous issue to compare yet.'}</div>}
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30">
          <div className="text-xs font-bold text-on-surface uppercase">Exceedance indicator</div>
          <div className="text-2xl font-bold font-mono text-on-surface mt-1">
            <Traceable field="probability">{summary.uncertainty?.probability ?? summary.uncertainty?.hazard_exceedance_indicator_pct ?? '—'}%</Traceable>
          </div>
          <div className="text-[11px] text-on-surface-variant mt-1 flex items-start gap-1">
            <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0 text-amber-600" /> Uncalibrated indicator of exceeding {summary.uncertainty?.threshold} {unit}, not a probability.
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-on-surface uppercase">Verification</span>
            <button onClick={() => setActiveRoute('verification')} className="text-[10px] text-primary flex items-center gap-0.5">centre <ArrowRight className="w-3 h-3" /></button>
          </div>
          <div className="text-lg font-bold font-mono text-on-surface mt-1">{verifyStage?.status === 'PENDING' ? 'Awaiting observation' : verifyStage?.status || '—'}</div>
          <div className="text-[11px] text-on-surface-variant mt-1">
            Open stage 14 in the trace above to record an observation or look up the IMD gridded value. Skill evidence: {
              Object.values(summary.skill_provenance || {}).every(p => p === 'DATABASE_VERIFIED_HISTORY') && Object.keys(summary.skill_provenance || {}).length
                ? 'verified history' : 'priors / scenario (not yet verified here)'}
          </div>
        </div>
      </section>
    </div>
  );
};
