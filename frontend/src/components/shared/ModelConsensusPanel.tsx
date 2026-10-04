import React from 'react';
import { ModelId } from '../../types';
import { Sparkles, Layers } from 'lucide-react';
import { useVaruna } from '../../context/VarunaContext';
import { modelInfo } from '../../utils/models';
import { Traceable } from './Traceable';

interface ModelConsensusPanelProps {
  modelForecasts: Partial<Record<ModelId, number | null>>;
  fusedValue: number;
  baselines: {
    simple_average: number;
    static_blend: number;
  };
  unit?: string;
}

export const ModelConsensusPanel: React.FC<ModelConsensusPanelProps> = ({
  modelForecasts,
  fusedValue,
  baselines,
  unit = 'mm'
}) => {
  const { summary } = useVaruna();
  // Render whatever model set the pipeline ran with (classic slots or live public models)
  const models = Object.keys(modelForecasts).map(id => ({ id, info: modelInfo(id, summary.source_meta?.[id]) }));

  return (
    <div className="p-3.5 rounded-lg bg-surface/90 border border-surface-border flex flex-col gap-3">
      <div className="flex items-center justify-between pb-1 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-primary" />
          <span className="font-headline font-semibold text-on-surface text-sm">
            FORECAST CONSENSUS vs VARUNA BLEND
          </span>
        </div>
        <span className="text-[11px] font-mono text-on-surface-variant">
          Units: <strong className="text-on-surface">{unit}</strong>
        </span>
      </div>

      {/* Grid of model forecasts */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-2.5">
        {models.map((m) => {
          const val = modelForecasts[m.id as ModelId];
          return (
            <div 
              key={m.id}
              className="p-2.5 rounded-md border border-outline-variant/30 bg-surface-container-low flex flex-col justify-between"
              style={{ borderLeft: `3px solid ${m.info.hex}` }}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-headline font-bold text-xs text-on-surface">{m.info.label}</span>
                </div>
                <div className="text-[9px] font-mono text-on-surface-variant truncate">{m.info.role}</div>
              </div>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="font-mono text-xl font-bold tracking-tight text-on-surface">
                  <Traceable field="model_forecast" model={m.id} glyph={false}>{val == null ? '—' : val.toFixed(1)}</Traceable>
                </span>
                <span className="font-mono text-[10px] text-on-surface-variant">{unit}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* VARUNA Primary Fused Hero Comparison Row */}
      <div className="p-3 rounded-lg bg-gradient-to-r from-cyan-50 via-surface-card to-sky-50 dark:from-cyan-950/80 dark:to-sky-950/80 border border-cyan-500/50 flex flex-wrap items-center justify-between gap-3 shadow-glow-cyan/20">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-cyan-500/20 border border-cyan-400 flex items-center justify-center text-primary">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-headline font-bold text-base text-primary tracking-wide">
                VARUNA ADAPTIVE FUSION
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-high text-on-surface border border-outline-variant/40">
                {summary.strategy || 'ADAPTIVE'}
              </span>
            </div>
            <div className="text-[11px] font-mono text-on-surface-variant">
              Trust-weighted combination; hover any number for its formula and sources
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Baselines pill */}
          <div className="hidden sm:flex flex-col items-end text-[11px] font-mono text-on-surface-variant border-r border-cyan-800/40 pr-4">
            <div>
              Simple Avg: <Traceable field="simple_average" glyph={false} className="text-on-surface font-semibold">{baselines.simple_average?.toFixed(1)} {unit}</Traceable>
            </div>
            <div>
              Static Blend: <Traceable field="static_blend" glyph={false} className="text-on-surface font-semibold">{baselines.static_blend?.toFixed(1)} {unit}</Traceable>
            </div>
          </div>

          {/* Value Display */}
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono text-3xl font-extrabold text-primary tracking-tight">
              <Traceable field="fused_value" glyph={false}>{fusedValue?.toFixed(1)}</Traceable>
            </span>
            <span className="font-mono text-sm text-primary font-medium">{unit}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
