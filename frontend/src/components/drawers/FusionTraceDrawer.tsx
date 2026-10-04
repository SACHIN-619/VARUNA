import React, { useState, useEffect } from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { fetchFusionTrace } from '../../services/api';
import { X, Sparkles, TrendingUp, ShieldCheck, AlertCircle } from 'lucide-react';
import { ProvenanceBadge } from '../shared/ProvenanceBadge';

export const FusionTraceDrawer: React.FC = () => {
  const { activeTraceModel, setActiveTraceModel, regionId, variable, leadHours, weatherRegime } = useVaruna();
  const [traceData, setTraceData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!activeTraceModel) return;
    setLoading(true);
    fetchFusionTrace(regionId, variable, leadHours, weatherRegime)
      .then((data) => {
        const item = data.active_trace?.find((t: any) => t.model_id === activeTraceModel) || data.active_trace?.[0];
        setTraceData(item);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [activeTraceModel, regionId, variable, leadHours, weatherRegime]);

  if (!activeTraceModel) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div className="w-full max-w-md bg-surface-container-lowest border-l border-outline-variant/30 h-full overflow-y-auto p-6 flex flex-col justify-between shadow-2xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded bg-primary/10 border border-primary/30 flex items-center justify-center text-primary">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-headline font-bold text-base text-on-surface">
                  FUSION TRACE ENGINE
                </h3>
                <span className="text-[11px] font-mono text-primary font-semibold">
                  Explainable AI (XAI) Attribution
                </span>
              </div>
            </div>
            <button 
              onClick={() => setActiveTraceModel(null)}
              className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="SUPERVISED GBDT + SOFTMAX ATTRIBUTION" />

          {/* Target Model Banner */}
          <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/30 flex items-center justify-between shadow-xs">
            <div>
              <span className="text-[11px] font-mono text-on-surface-variant uppercase tracking-wide">
                Target Model Source
              </span>
              <div className="font-headline font-extrabold text-2xl text-on-surface flex items-center gap-2">
                {activeTraceModel}
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-primary-container text-on-primary-container font-bold">
                  {traceData?.percentage ?? 46}% TRUST
                </span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-[11px] font-mono text-on-surface-variant">Cycle Shift</span>
              <div className="font-mono text-sm font-bold text-emerald-600 flex items-center justify-end gap-1">
                <TrendingUp className="w-4 h-4" />
                {traceData?.delta_from_previous > 0 ? `+${traceData.delta_from_previous}%` : `${traceData?.delta_from_previous ?? 0}%`}
              </div>
            </div>
          </div>

          {/* Rationale explanation */}
          <div className="p-3.5 rounded-lg bg-surface-container-low border border-outline-variant/30 text-xs text-on-surface leading-relaxed font-body">
            <strong className="text-primary block mb-1 font-headline">Scientific Attribution Rationale:</strong>
            {traceData?.rationale || "Assigned dominant trust conditioned on historical monsoon trough tracking accuracy and low error variance across 48h lead horizon."}
          </div>

          {/* Factor Breakdown Bars */}
          <div className="space-y-3">
            <h4 className="font-headline font-semibold text-xs text-on-surface-variant tracking-wider uppercase">
              Attribution Contributors (0 - 100 Score)
            </h4>

            {traceData?.contributors && (
              <div className="space-y-3 font-mono text-xs">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Regional Historical Skill:</span>
                    <span className="text-on-surface font-bold">{traceData.contributors.regional_skill}%</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden border border-outline-variant/30">
                    <div className="h-full bg-primary rounded-full" style={{ width: `${traceData.contributors.regional_skill}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Recent Verification Score:</span>
                    <span className="text-on-surface font-bold">{traceData.contributors.recent_error}%</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden border border-outline-variant/30">
                    <div className="h-full bg-teal-500 rounded-full" style={{ width: `${traceData.contributors.recent_error}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Lead-Time Horizon Reliability:</span>
                    <span className="text-on-surface font-bold">{traceData.contributors.lead_reliability}%</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden border border-outline-variant/30">
                    <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${traceData.contributors.lead_reliability}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Weather Regime Suitability:</span>
                    <span className="text-on-surface font-bold">{traceData.contributors.weather_regime}%</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden border border-outline-variant/30">
                    <div className="h-full bg-sky-500 rounded-full" style={{ width: `${traceData.contributors.weather_regime}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Disagreement Penalty Impact:</span>
                    <span className="text-amber-600 font-bold">-{traceData.contributors.disagreement_penalty}%</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden border border-outline-variant/30">
                    <div className="h-full bg-amber-500 rounded-full" style={{ width: `${traceData.contributors.disagreement_penalty}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Source Feed Availability:</span>
                    <span className="text-emerald-600 font-bold">{traceData.contributors.availability}%</span>
                  </div>
                  <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden border border-outline-variant/30">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${traceData.contributors.availability}%` }} />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer actions */}
        <div className="pt-6 border-t border-outline-variant/30">
          <button
            onClick={() => setActiveTraceModel(null)}
            className="w-full py-2.5 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-mono text-xs border border-outline-variant/30 font-semibold transition-colors"
          >
            Close Decomposition
          </button>
        </div>
      </div>
    </div>
  );
};
