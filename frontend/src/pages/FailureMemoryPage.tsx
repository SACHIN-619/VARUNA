import React, { useState } from 'react';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { FailureMemoryRecord } from '../types';
import { BrainCircuit, AlertTriangle, TrendingUp, TrendingDown, Minus, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const FailureMemoryPage: React.FC = () => {
  const records: FailureMemoryRecord[] = [
    {
      model_id: 'WRF',
      region_name: 'Telangana (Deccan Catchment)',
      lead_hours: 72,
      regime: 'HEAVY_RAINFALL',
      signal: 'Error Variance Escalation',
      observed_pattern: 'Recent convective dampening caused +18.4mm under-prediction of convective core.',
      trust_response: 'Weight reduced from 35% to 31% via EMA penalty.',
      verification_history: '3 consecutive cycles with residual error > 15mm under heavy rainfall.'
    },
    {
      model_id: 'GFS',
      region_name: 'Odisha Coastal Corridor',
      lead_hours: 48,
      regime: 'CONVECTIVE',
      signal: 'Systematic Wet Bias Clamped',
      observed_pattern: 'Forecast 103mm vs observed 42mm. Consistent +4.8mm positive bias.',
      trust_response: 'Hard weight ceiling clamped to 5% under active Southwest Monsoon.',
      verification_history: 'Known climatological moist bias over peninsular and coastal basins.'
    },
    {
      model_id: 'AI_WEATHER',
      region_name: 'Kerala & Western Ghats',
      lead_hours: 72,
      regime: 'HEAVY_RAINFALL',
      signal: 'Peak Smoothing Detected',
      observed_pattern: 'Global graph neural network smoothed isolated cloudburst peak (88mm observed vs 64mm predicted).',
      trust_response: 'Sub-allocated to WRF 3km for short-range orographic bursts; retained for synoptic trend.',
      verification_history: 'Low spread, but tendency to clip extreme localized tails.'
    },
    {
      model_id: 'NCUM',
      region_name: 'Gangetic West Bengal',
      lead_hours: 48,
      regime: 'NORMAL',
      signal: 'High Synoptic Lock-in',
      observed_pattern: 'Radar Doppler data assimilation yielded 96.2% parity with ground truth.',
      trust_response: 'Dominant trust allocation boosted to 49%.',
      verification_history: 'Consistent top rank across last 20 verified cycles.'
    }
  ];

  const [selectedRecord, setSelectedRecord] = useState<FailureMemoryRecord>(records[0]);

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-purple-600 dark:text-purple-400 font-bold uppercase tracking-wider">
              Signature VARUNA Intelligence Capability
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="REGIME-CONDITIONED FAILURE PROFILES" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            MODEL FAILURE MEMORY & TRUST DRIFT
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Automated tracking of regime-dependent model vulnerabilities, conditional error penalties, and dynamic weight drift.
          </p>
        </div>
      </div>

      {/* Trust Drift Summary Strip */}
      <div className="p-5 rounded-2xl bg-surface border border-surface-border flex flex-wrap items-center justify-between gap-4 shadow-md">
        <div>
          <span className="text-[10px] font-mono text-on-surface-variant uppercase tracking-wider block mb-1">
            Current Cycle Trust Drift Indicators
          </span>
          <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5 p-2 rounded-lg bg-surface-deep border border-emerald-500/30">
              <span className="font-bold text-on-surface">NCUM:</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-bold flex items-center">42% → 46% <TrendingUp className="w-3.5 h-3.5 ml-1" /></span>
            </div>
            <div className="flex items-center gap-1.5 p-2 rounded-lg bg-surface-deep border border-rose-500/30">
              <span className="font-bold text-on-surface">WRF:</span>
              <span className="text-rose-600 dark:text-rose-400 font-bold flex items-center">35% → 31% <TrendingDown className="w-3.5 h-3.5 ml-1" /></span>
            </div>
            <div className="flex items-center gap-1.5 p-2 rounded-lg bg-surface-deep border border-outline-variant">
              <span className="font-bold text-on-surface">AI Weather:</span>
              <span className="text-on-surface-variant font-bold flex items-center">18% → 18% <Minus className="w-3.5 h-3.5 ml-1" /></span>
            </div>
            <div className="flex items-center gap-1.5 p-2 rounded-lg bg-surface-deep border border-outline-variant">
              <span className="font-bold text-on-surface">GFS:</span>
              <span className="text-on-surface-variant font-bold flex items-center">5% → 5% <Minus className="w-3.5 h-3.5 ml-1" /></span>
            </div>
          </div>
        </div>

        <div className="text-xs font-mono text-on-surface-variant max-w-xs">
          Trust drift triggered by rolling residual errors from the latest verification cycle.
        </div>
      </div>

      {/* Main Grid: Failure Memory Table & Profile Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Table (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-3">
          <div className="rounded-xl bg-surface border border-surface-border overflow-hidden shadow-lg">
            <div className="p-3.5 bg-surface-deep border-b border-surface-border flex items-center justify-between text-xs font-mono text-on-surface-variant">
              <span>CONDITIONAL FAILURE MEMORY TABLE</span>
              <span>VERIFY → LEARN → TRUST</span>
            </div>

            <div className="divide-y divide-surface-border">
              {records.map((r, idx) => {
                const isSelected = selectedRecord.model_id === r.model_id && selectedRecord.region_name === r.region_name;
                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedRecord(r)}
                    className={`p-4 transition-colors cursor-pointer flex items-center justify-between ${
                      isSelected ? 'bg-purple-50 dark:bg-purple-950/40 border-l-4 border-purple-400' : 'hover:bg-surface-card'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-headline font-bold text-sm text-on-surface">{r.model_id}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-surface-border text-on-surface-variant">
                          {r.region_name}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-50 dark:bg-purple-950 text-purple-600 dark:text-purple-400 border border-purple-800">
                          +{r.lead_hours}H
                        </span>
                      </div>
                      <div className="text-xs font-mono text-amber-600 dark:text-amber-400 font-semibold">{r.signal}</div>
                      <div className="text-[11px] font-mono text-on-surface-variant truncate max-w-md">{r.observed_pattern}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Failure Profile Inspector (5 cols) */}
        <div className="lg:col-span-5">
          <div className="p-5 rounded-xl bg-surface border border-surface-border flex flex-col gap-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <span className="text-xs font-mono text-purple-600 dark:text-purple-400 uppercase font-semibold flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                FAILURE DOSSIER & ADAPTIVE RESPONSE
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface-card text-on-surface-variant border border-surface-border">
                {selectedRecord.model_id}
              </span>
            </div>

            <div>
              <div className="text-xs font-mono text-on-surface-variant uppercase">Target Condition</div>
              <h3 className="font-headline font-extrabold text-lg text-on-surface mt-0.5">
                {selectedRecord.region_name}
              </h3>
              <div className="text-xs font-mono text-primary mt-1">
                Horizon: +{selectedRecord.lead_hours}H • Regime: {selectedRecord.regime}
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-surface-deep border border-surface-border space-y-2 text-xs font-mono">
              <div>
                <span className="text-on-surface-variant block mb-0.5 font-bold">Observed Failure Mode:</span>
                <p className="text-on-surface leading-relaxed font-sans text-xs">{selectedRecord.observed_pattern}</p>
              </div>
              <div className="pt-2 border-t border-surface-border">
                <span className="text-primary block mb-0.5 font-bold">Trust Engine Response:</span>
                <p className="text-primary leading-relaxed font-sans text-xs font-semibold">{selectedRecord.trust_response}</p>
              </div>
              <div className="pt-2 border-t border-surface-border">
                <span className="text-on-surface-variant block mb-0.5 font-bold">Verification Evidence:</span>
                <p className="text-on-surface-variant leading-relaxed font-sans text-xs">{selectedRecord.verification_history}</p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-950/30 border border-purple-600/30 text-xs font-mono text-purple-200">
              <strong>Simplex Assurance:</strong> When a model is penalized under specific regimes, its weight is smoothly shifted to the best-performing model without manual intervention.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
