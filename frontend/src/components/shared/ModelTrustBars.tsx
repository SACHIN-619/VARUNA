import React from 'react';
import { ModelWeight, ModelId } from '../../types';
import { useVaruna } from '../../context/VarunaContext';
import { modelInfo } from '../../utils/models';
import { ArrowUpRight, ArrowDownRight, Minus, Sparkles, AlertTriangle } from 'lucide-react';

interface ModelTrustBarsProps {
  weights: ModelWeight[];
  interactive?: boolean;
}

export const ModelTrustBars: React.FC<ModelTrustBarsProps> = ({ weights, interactive = true }) => {
  const { setActiveTraceModel, summary } = useVaruna();

  const getModelColor = (modelId: ModelId, status: string) =>
    status === 'DISABLED' ? 'bg-surface-container-highest text-slate-500 border-outline-variant' : modelInfo(modelId, summary.source_meta?.[modelId]).bar;

  const getModelBadge = (modelId: ModelId) => modelInfo(modelId, summary.source_meta?.[modelId]);

  return (
    <div className="flex flex-col gap-3 w-full">
      <div className="flex items-center justify-between text-xs font-mono text-on-surface-variant pb-1 border-b border-surface-border">
        <span>MODEL SOURCE & TRUST WEIGHT</span>
        <span>ALLOCATION (Σ = 1.0)</span>
      </div>

      <div className="space-y-2.5">
        {weights.map((w) => {
          const pct = Math.round(w.weight * 100);
          const badge = getModelBadge(w.model_id);
          const isDominant = w.weight >= 0.40;
          const isDisabled = w.status === 'DISABLED';

          return (
            <div 
              key={w.model_id}
              onClick={() => interactive && setActiveTraceModel(w.model_id)}
              className={`p-2.5 rounded-lg bg-surface/90 border border-surface-border transition-all duration-200 select-none ${
                interactive && !isDisabled 
                  ? 'cursor-pointer hover:border-cyan-500/60 hover:bg-surface-card hover:shadow-glow-cyan/20' 
                  : ''
              } ${isDisabled ? 'opacity-50' : ''}`}
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-headline font-bold text-on-surface text-sm">{w.model_id}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-container-high text-on-surface-variant border border-outline-variant">
                    {badge.label}
                  </span>
                  {isDominant && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-mono text-primary bg-cyan-50 dark:bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800/60">
                      <Sparkles className="w-2.5 h-2.5 text-primary" />
                      DOMINANT
                    </span>
                  )}
                  {isDisabled && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-mono text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/80 px-1.5 py-0.5 rounded border border-rose-800/60">
                      <AlertTriangle className="w-2.5 h-2.5 text-rose-600 dark:text-rose-400" />
                      OFFLINE (REBALANCED)
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-on-surface-variant">
                    Raw: <strong className="text-on-surface">{typeof w.raw_forecast === 'number' ? w.raw_forecast.toFixed(1) : (w.raw_forecast ?? 'N/A')}</strong> mm
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-base font-bold text-on-surface">
                      {isDisabled ? '0%' : `${pct}%`}
                    </span>
                    <span className="font-mono text-[10px] text-on-surface-variant">
                      ({typeof w.weight === 'number' ? w.weight.toFixed(4) : '0.0000'})
                    </span>
                  </div>
                </div>
              </div>

              {/* Progress Bar Container */}
              <div className="w-full h-3 bg-surface-deep rounded-full overflow-hidden p-0.5 border border-surface-border">
                <div 
                  className={`h-full rounded-full transition-all duration-700 ${getModelColor(w.model_id, w.status)}`}
                  style={{ width: `${Math.max(pct, isDisabled ? 0 : 3)}%` }}
                />
              </div>

              {/* Detail telemetry footer */}
              <div className="flex items-center justify-between text-[10px] font-mono text-on-surface-variant mt-1.5 pt-1">
                <span>Hist. MAE: <strong className="text-on-surface-variant">{typeof w.historical_mae === 'number' ? `${w.historical_mae.toFixed(1)}mm` : 'N/A'}</strong></span>
                {typeof w.recent_bias === 'number' && (
                  <span>
                    Recent Bias: <strong className={w.recent_bias > 2 ? 'text-amber-600 dark:text-amber-400' : 'text-on-surface-variant'}>
                      {w.recent_bias > 0 ? `+${w.recent_bias.toFixed(1)}` : w.recent_bias.toFixed(1)}mm
                    </strong>
                  </span>
                )}
                {interactive && !isDisabled && (
                  <span className="text-primary/80 hover:text-primary transition-colors flex items-center gap-0.5">
                    Click for XAI Trace <ArrowUpRight className="w-3 h-3" />
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-2.5 rounded bg-surface-deep/80 border border-surface-border/80 text-[11px] font-mono text-on-surface-variant flex items-start gap-2">
        <Sparkles className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
        <div>
          <strong className="text-on-surface">Adaptive Simplex Proof:</strong> Normalized weights guaranteed to satisfy{' '}
          <code className="text-primary font-bold">w_i ≥ 0, Σw_i = 1.0</code>. Click any model bar to decompose
          its exact mathematical attribution trace.
        </div>
      </div>
    </div>
  );
};
