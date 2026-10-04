import React from 'react';
import { useVaruna, formatBenchmark } from '../../context/VarunaContext';
import { ProvenanceBadge } from '../shared/ProvenanceBadge';
import { ShieldCheck, Activity, Cpu, Sparkles, AlertOctagon } from 'lucide-react';

export const SystemStatusBar: React.FC = () => {
  const { summary, simulatedDisabledModel, dataSourceStatus, benchmark } = useVaruna();
  // Everything below is derived from the live summary (it used to be hard-coded "healthy" text)
  const weights = summary?.weights || [];
  const active = weights.filter(w => w.weight > 0).length;
  const total = weights.length || 4;
  const degraded = active < total;
  const health = (summary as any)?.data_health?.status || (degraded ? 'DEGRADED' : 'HEALTHY');
  const strategy = (summary as any)?.strategy || 'ADAPTIVE_ML';
  const live = !!dataSourceStatus?.backendConnected;

  return (
    <div className="w-full bg-surface-container-low border-b border-outline-variant/30 px-4 py-1.5 flex flex-wrap items-center justify-between gap-2 text-xs font-mono select-none">
      {/* Left status nodes */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-on-surface">
          <span className={`w-2 h-2 rounded-full ${health === 'HEALTHY' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
          <span className="text-on-surface-variant">FEEDS:</span>
          <strong className={`font-bold ${health === 'HEALTHY' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>{health}</strong>
        </div>

        <span className="text-outline-variant hidden sm:inline">•</span>

        <div className="flex items-center gap-1.5 text-on-surface">
          <Activity className="w-3.5 h-3.5 text-primary" />
          <span className="text-on-surface-variant">MODELS:</span>
          <strong className={degraded ? 'text-amber-600 dark:text-amber-400 font-bold' : 'text-primary font-bold'}>
            {active}/{total} {degraded ? '(DEGRADED)' : 'ONLINE'}
          </strong>
        </div>

        <span className="text-outline-variant hidden sm:inline">•</span>

        <div className="flex items-center gap-1.5 text-on-surface">
          <Cpu className="w-3.5 h-3.5 text-tertiary" />
          <span className="text-on-surface-variant">TRUST ENGINE:</span>
          <strong className="text-tertiary font-bold">{strategy === 'ADAPTIVE_RELIABILITY' ? 'ADAPTIVE RELIABILITY' : 'GBDT + SOFTMAX'}</strong>
        </div>

        <span className="text-outline-variant hidden md:inline">•</span>

        <div className="flex items-center gap-1.5 text-on-surface hidden md:flex">
          <ShieldCheck className="w-3.5 h-3.5 text-on-surface-variant" />
          <span className="text-on-surface-variant">VERIFICATION:</span>
          <strong className="text-on-surface font-bold">AWAITING OBSERVATIONS</strong>
        </div>
      </div>

      {/* Right Provenance Notification */}
      <div className="flex items-center gap-2">
        {simulatedDisabledModel && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-error-container text-on-error-container text-[10px] font-bold">
            <AlertOctagon className="w-3 h-3" />
            FEED INTERRUPTED ({simulatedDisabledModel})
          </span>
        )}
        <ProvenanceBadge
          type="CONTROLLED_BENCHMARK"
          label={live ? 'LIVE BACKEND · SYNTHETIC SCENARIO' : 'OFFLINE DEMO (SYNTHETIC)'}
        />
        <span className="hidden lg:inline-flex px-2 py-0.5 rounded bg-secondary-fixed text-on-secondary-fixed-variant text-[11px] font-bold">
          {formatBenchmark(benchmark)}
        </span>
      </div>
    </div>
  );
};
