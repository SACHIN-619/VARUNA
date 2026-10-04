import React from 'react';
import { DisagreementInfo, UncertaintyInfo } from '../../types';
import { AlertCircle, HelpCircle, Activity } from 'lucide-react';

interface DisagreementMeterProps {
  disagreement: DisagreementInfo;
  uncertainty: UncertaintyInfo;
  modelValues?: Record<string, number>;
  fusedValue?: number;
}

export const DisagreementMeter: React.FC<DisagreementMeterProps> = ({
  disagreement,
  uncertainty,
  modelValues = { NCUM: 82.0, WRF: 47.0, AI_WEATHER: 64.0, GFS: 103.0 },
  fusedValue = 70.1
}) => {
  const vals = Object.values(modelValues);
  const minVal = Math.min(...vals, fusedValue);
  const maxVal = Math.max(...vals, fusedValue);
  const rangeSpan = Math.max(maxVal - minVal, 10);
  const paddingMin = Math.max(0, Math.floor(minVal - 10));
  const paddingMax = Math.ceil(maxVal + 10);
  const fullSpan = paddingMax - paddingMin;

  const getPercent = (val: number) => {
    return Math.min(100, Math.max(0, ((val - paddingMin) / fullSpan) * 100));
  };

  const getConfidenceBadge = (conf: string) => {
    switch (conf) {
      case 'VERY_HIGH':
      case 'HIGH':
        return { text: 'HIGH', color: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/80 border-emerald-600/40' };
      case 'MEDIUM':
        return { text: 'MEDIUM', color: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/80 border-amber-600/40' };
      default:
        return { text: 'LOW', color: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/80 border-rose-600/40' };
    }
  };

  const getDisagreementColor = (lvl: string) => {
    switch (lvl) {
      case 'HIGH':
        return 'text-amber-600 dark:text-amber-400 border-amber-500/40 bg-amber-50 dark:bg-amber-950/40';
      case 'MEDIUM':
        return 'text-primary border-sky-500/40 bg-sky-50 dark:bg-sky-950/40';
      default:
        return 'text-emerald-600 dark:text-emerald-400 border-emerald-500/40 bg-emerald-50 dark:bg-emerald-950/40';
    }
  };

  const spreadVal = disagreement?.forecast_spread ?? 23.8;
  const probVal = uncertainty?.probability ?? 78.4;
  const confLvl = uncertainty?.confidence || 'MEDIUM';
  const disLvl = disagreement?.disagreement_level || 'HIGH';

  const confBadge = getConfidenceBadge(confLvl);

  return (
    <div className="p-3.5 rounded-lg bg-surface/90 border border-surface-border flex flex-col gap-3">
      {/* Header telemetry */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          <span className="font-headline font-semibold text-on-surface text-sm">
            ENSEMBLE DISAGREEMENT & CONFIDENCE
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${getDisagreementColor(disLvl)}`}>
            SPREAD: {disLvl}
          </span>
          <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${confBadge.color}`}>
            CONFIDENCE: {confBadge.text}
          </span>
        </div>
      </div>

      {/* Range and Distribution visualizer */}
      <div className="pt-2 pb-1">
        <div className="relative w-full h-10 bg-surface-deep rounded-md border border-surface-border/80 px-2 flex items-center">
          {/* Background grid markings */}
          <div className="absolute inset-0 flex justify-between px-3 items-center opacity-20 pointer-events-none">
            <div className="h-full border-r border-outline-variant"></div>
            <div className="h-full border-r border-outline-variant"></div>
            <div className="h-full border-r border-outline-variant"></div>
            <div className="h-full border-r border-outline-variant"></div>
          </div>

          {/* Spread span highlight band */}
          <div 
            className="absolute h-4 rounded bg-amber-500/20 border border-amber-500/50"
            style={{
              left: `${getPercent(minVal)}%`,
              width: `${Math.max(4, getPercent(maxVal) - getPercent(minVal))}%`
            }}
          />

          {/* Model Points */}
          {Object.entries(modelValues).map(([mId, val]) => (
            <div
              key={mId}
              title={`${mId}: ${typeof val === 'number' ? val.toFixed(1) : val} mm`}
              className="absolute -top-1 -translate-x-1/2 flex flex-col items-center group cursor-pointer z-10"
              style={{ left: `${getPercent(val || 0)}%` }}
            >
              <span className="text-[9px] font-mono text-on-surface-variant group-hover:text-primary transition-colors">
                {mId === 'AI_WEATHER' ? 'AI' : mId}
              </span>
              <div className="w-2.5 h-2.5 rounded-full bg-slate-300 border border-slate-900 group-hover:scale-125 transition-transform" />
            </div>
          ))}

          {/* VARUNA Fused Marker */}
          <div 
            title={`VARUNA Fused: ${typeof fusedValue === 'number' ? fusedValue.toFixed(1) : fusedValue} mm`}
            className="absolute -top-3 -translate-x-1/2 flex flex-col items-center z-20"
            style={{ left: `${getPercent(fusedValue || 0)}%` }}
          >
            <span className="text-[10px] font-mono font-bold text-primary bg-cyan-50 dark:bg-cyan-950 px-1 rounded border border-cyan-500 shadow-glow-cyan/40">
              VARUNA: {typeof fusedValue === 'number' ? fusedValue.toFixed(1) : fusedValue}
            </span>
            <div className="w-3.5 h-3.5 rounded-full bg-cyan-400 border-2 border-slate-900 shadow-glow-cyan" />
          </div>
        </div>

        {/* X-axis calibration labels */}
        <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1.5 px-1">
          <span>{paddingMin} mm</span>
          <span>Forecast Spread: ±{typeof spreadVal === 'number' ? spreadVal.toFixed(1) : spreadVal} mm</span>
          <span>{paddingMax} mm</span>
        </div>
      </div>

      {/* Critical Scientific Clarification Box */}
      <div className="p-2.5 rounded bg-surface-deep/90 border border-surface-border text-xs text-on-surface-variant flex items-start gap-2">
        <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="text-[11px] leading-relaxed">
          <strong className="text-amber-600 dark:text-amber-400">Epistemic Uncertainty vs Event Probability:</strong>{' '}
          Event probability is <span className="font-mono font-bold text-on-surface">{typeof probVal === 'number' ? probVal.toFixed(1) : probVal}%</span>, 
          yet operational confidence is downgraded to <strong className="text-amber-600 dark:text-amber-400 font-mono">{confLvl}</strong>. 
          Confidence reflects multi-model agreement ({typeof minVal === 'number' ? minVal.toFixed(1) : minVal}mm vs {typeof maxVal === 'number' ? maxVal.toFixed(1) : maxVal}mm span), not simply threshold probability.
        </div>
      </div>
    </div>
  );
};
