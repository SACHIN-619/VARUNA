import React, { useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { Clock, TrendingUp, TrendingDown, ChevronDown, ChevronUp, AlertCircle, ArrowRight } from 'lucide-react';

export const WhatChangedPage: React.FC = () => {
  const { summary } = useVaruna();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const wc: any = summary.what_changed || {};
  const MODELS: Array<[string, string]> = [['NCUM', 'NCUM'], ['WRF', 'WRF'], ['AI_WEATHER', 'AI Weather'], ['GFS', 'GFS']];
  const curW: Record<string, number> = wc.current_weights || Object.fromEntries((summary.weights || []).map(w => [w.model_id, w.weight]));
  const prevW: Record<string, number> = wc.previous_weights || {};
  const shift: Record<string, number> = wc.weight_shifts_pct_points || {};
  const pct = (v?: number) => (typeof v === 'number' ? `${Math.round(v * 100)}%` : '—');
  const timelineEvents = (wc.timeline && wc.timeline.length ? wc.timeline : null) || [
    { time: "00:00 UTC", event: "NCUM trust adjusted", detail: "42% → 46% following regional score verification against Telangana AWS surface stations.", type: "trust" },
    { time: "02:00 UTC", event: "WRF recent error increased", detail: "Observed vs forecast delta reached 18.4mm in Deccan Catchment, triggering an automatic penalty.", type: "error" },
    { time: "04:00 UTC", event: "Model disagreement escalated", detail: "Spread widened to 56.0mm across ensemble members (WRF 47mm vs GFS 103mm).", type: "disagreement" },
    { time: "06:00 UTC", event: "Fusion weights re-normalized", detail: "Simplex engine reallocated weight vector: NCUM 46%, WRF 31%, AI 18%, GFS 5%.", type: "fusion" },
    { time: "08:00 UTC", event: "Operational confidence calibrated", detail: "Confidence downgraded from HIGH to MEDIUM to reflect substantial epistemic spread.", type: "confidence" }
  ];

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider">
              Cycle Evolution Diagnostics
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="CYCLE-TO-CYCLE DELTA AUDIT" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            WHAT CHANGED SINCE PREVIOUS CYCLE?
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Audit trail of how incoming verification data, forecast error drift, and model spread shifted trust weights over time.
          </p>
        </div>
      </div>

      {/* Before / After Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Previous Cycle (computed by the backend for the same valid time) */}
        <div className="p-5 rounded-xl bg-surface border border-surface-border">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border mb-3">
            <span className="text-xs font-mono text-on-surface-variant uppercase font-bold">Previous Forecast Cycle</span>
            <span className="text-xs font-mono text-on-surface-variant">T-24H · same valid time</span>
          </div>
          <div className="space-y-3 font-mono text-xs">
            {MODELS.map(([id, name]) => (
              <div key={id} className="flex justify-between items-center p-2 rounded bg-surface-deep">
                <span className="text-on-surface-variant">{name} Trust:</span>
                <strong className="text-on-surface text-sm">{pct(prevW[id])}</strong>
              </div>
            ))}
            <div className="pt-2 border-t border-surface-border flex justify-between text-on-surface-variant">
              <span>Fused: {wc.previous_value ?? '—'} {summary.unit}</span>
              <span>Confidence: {String(wc.confidence_shift || '').split('->')[0].trim() || '—'}</span>
            </div>
          </div>
        </div>

        {/* Current Cycle */}
        <div className="p-5 rounded-xl bg-gradient-to-br from-cyan-50 dark:from-cyan-950/40 via-surface to-surface border border-cyan-500/40">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border mb-3">
            <span className="text-xs font-mono text-primary uppercase font-bold">Current Active Cycle</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-50 dark:bg-cyan-950 text-primary border border-cyan-800">ACTIVE NOW</span>
          </div>
          <div className="space-y-3 font-mono text-xs">
            {MODELS.map(([id, name]) => {
              const d = shift[id];
              return (
                <div key={id} className={`flex justify-between items-center p-2 rounded bg-surface-deep border ${d > 0.5 ? 'border-emerald-500/30' : d < -0.5 ? 'border-rose-500/30' : 'border-transparent'}`}>
                  <span className="text-on-surface">{name} Trust:</span>
                  <div className="flex items-center gap-1.5">
                    {typeof d === 'number' && Math.abs(d) >= 0.5 && (
                      <span className={`text-xs font-bold ${d > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                        ({d > 0 ? '+' : ''}{d.toFixed(1)} pts)
                      </span>
                    )}
                    <strong className="text-primary text-sm">{pct(curW[id])}</strong>
                  </div>
                </div>
              );
            })}
            <div className="pt-2 border-t border-surface-border flex justify-between text-primary font-bold">
              <span>Fused: {summary.fused_forecast?.toFixed?.(1) ?? '—'} {summary.unit} {typeof wc.fused_delta === 'number' ? `(${wc.fused_delta > 0 ? '+' : ''}${wc.fused_delta})` : ''}</span>
              <span className="text-amber-600 dark:text-amber-400">Confidence: {summary.uncertainty?.confidence ?? '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Driver Banner */}
      <div className="p-4 rounded-xl bg-surface border border-surface-border flex items-start gap-3 text-xs font-mono">
        <AlertCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-on-surface block">Primary Synthesis Driver:</strong>
          <p className="text-on-surface-variant leading-relaxed font-sans text-xs">
            {summary.what_changed.primary_driver}
          </p>
        </div>
      </div>

      {/* Cycle Event Stream Timeline */}
      <div className="p-6 rounded-xl bg-surface border border-surface-border">
        <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-primary" />
          <span>Operational Event Stream Timeline</span>
        </h3>

        <div className="relative border-l-2 border-surface-border ml-3 pl-6 space-y-6">
          {timelineEvents.map((item, idx) => {
            const isExpanded = expandedIndex === idx;
            return (
              <div key={idx} className="relative group">
                {/* Node icon beacon */}
                <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-surface-deep border-2 border-cyan-400 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                </div>

                <div 
                  onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                  className="p-3.5 rounded-lg bg-surface-deep border border-surface-border hover:border-cyan-500/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-primary">{item.time}</span>
                      <span className="text-slate-600 font-mono text-xs">•</span>
                      <span className="font-headline font-bold text-sm text-on-surface">{item.event}</span>
                    </div>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-on-surface-variant" /> : <ChevronDown className="w-4 h-4 text-on-surface-variant" />}
                  </div>

                  <div className="text-xs font-mono text-on-surface-variant mt-1">
                    {item.detail}
                  </div>

                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-surface-border text-xs font-mono text-on-surface-variant space-y-1 animate-fadeIn">
                      <div>Event Category: <strong className="text-primary uppercase">{item.type}</strong></div>
                      <div>Provenance Lock: <span className="text-emerald-600 dark:text-emerald-400">CONTROLLED_CHRONOLOGICAL_BENCHMARK</span></div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
