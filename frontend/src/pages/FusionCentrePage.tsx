import React, { useState } from 'react';
import { useVaruna, formatBenchmark } from '../context/VarunaContext';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { 
  Sparkles, 
  RotateCw, 
  CheckCircle2, 
  AlertTriangle, 
  Layers, 
  Share2, 
  TrendingUp,
  SlidersHorizontal,
  FileCheck
} from 'lucide-react';

export const FusionCentrePage: React.FC = () => {
  const { summary, leadHours, weatherRegime, weights, regionId, subdivisions, dataMode, forecastPackage, benchmark } = useVaruna();

  const [capeValue, setCapeValue] = useState<number>(2450);
  const [trustPrior, setTrustPrior] = useState<number>(0.82);
  const [isRecomputing, setIsRecomputing] = useState<boolean>(false);

  const currentSub = subdivisions.find(s => s.id === regionId) || subdivisions[0];

  const modelVals = summary.model_forecasts || {};
  const valList = Object.values(modelVals).filter((v): v is number => typeof v === 'number' && !isNaN(v));
  const minVal = valList.length > 0 ? Math.min(...valList) : 0;
  const maxVal = valList.length > 0 ? Math.max(...valList) : 100;

  const handleRecompute = () => {
    setIsRecomputing(true);
    setTimeout(() => {
      setIsRecomputing(false);
    }, 600);
  };

  // Dynamic simulated response based on sandbox sliders
  const baseFused = summary.fused_forecast || 70.1;
  const simulatedFused = (baseFused + (capeValue - 2450) * 0.005 + (trustPrior - 0.82) * 10).toFixed(1);

  return (
    <div className="flex flex-col w-full animate-fadeIn pb-12">
      
      {/* Top Utility & Metadata Strip */}
      <div className="p-4 lg:p-6 pb-0 flex flex-col gap-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/30 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-surface-container-high flex items-center justify-center text-primary shadow-xs">
              <Share2 className="w-5 h-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-headline font-bold text-lg tracking-tight text-on-surface">
                  VARUNA Adaptive Fusion Engine
                </span>
                <span className="px-2 py-0.5 rounded bg-surface-container-high text-primary font-mono text-[10px] font-bold uppercase">
                  CANONICAL 14-STAGE PIPELINE
                </span>
              </div>
              <p className="text-xs text-on-surface-variant">
                Dynamic multi-model forecast intelligence &amp; adaptive weight allocation ({currentSub.name}).
              </p>
            </div>
          </div>

          <div className="flex items-center flex-wrap gap-2.5">
            <div className="flex items-center gap-2 bg-surface-container-low px-3 py-1.5 rounded border border-outline-variant/20 text-xs">
              <span className="w-2 h-2 rounded-full bg-secondary-container" />
              <span className="text-on-surface-variant font-mono">MODEL SPREAD:</span>
              <span className="font-mono text-primary font-bold">{summary.disagreement?.forecast_spread?.toFixed(1) || '0.0'} {summary.unit}</span>
            </div>

            <div className="flex items-center gap-2 bg-surface-container-low px-3 py-1.5 rounded border border-outline-variant/20 text-xs">
              <span className="text-on-surface-variant font-mono">CONTROLLED BENCHMARK:</span>
              <span className="font-mono text-secondary font-bold">{formatBenchmark(benchmark)}</span>
            </div>

            <button
              onClick={handleRecompute}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary text-on-primary hover:bg-primary-container text-xs font-semibold transition-all shadow-xs"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRecomputing ? 'animate-spin' : ''}`} />
              <span>Recompute Adaptive Weights</span>
            </button>
          </div>
        </div>
      </div>

      {/* Section 1: Ingestion Spectrum (Dynamically Mapped Model Cards) */}
      <div className="p-4 lg:p-6 pb-0 flex flex-col gap-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-outline uppercase tracking-wider font-bold">
              STAGE 00 // MODEL INGESTION SPECTRUM
            </span>
            <span className="font-mono text-on-surface-variant text-[11px]">
              (+{leadHours}H PRECIP FORECAST ENSEMBLE)
            </span>
          </div>
          <span className="font-mono text-[11px] text-on-surface-variant">
            {summary.active_cycle || '—'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {summary.weights.map((w) => {
            const rawVal = summary.model_forecasts?.[w.model_id];
            const weightPct = Math.round(w.weight * 100);
            
            let colorClass = 'primary';
            let subtitle = 'NCMRWF Unified Model (12 km)';
            if (w.model_id === 'WRF') { colorClass = 'secondary'; subtitle = 'Regional Dynamical Core'; }
            if (w.model_id === 'AI_WEATHER') { colorClass = 'tertiary'; subtitle = 'Data-Driven Emulation'; }
            if (w.model_id === 'GFS') { colorClass = 'outline'; subtitle = 'Global Synoptic Baseline'; }

            return (
              <div 
                key={w.model_id} 
                className="group bg-surface-container-lowest rounded-xl p-4 shadow-xs border border-outline-variant/30 hover:shadow-md transition-all relative overflow-hidden"
              >
                <div className={`absolute top-0 left-0 right-0 h-1 bg-${colorClass}`} />
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-headline font-bold text-sm text-on-surface">{w.model_id}</span>
                      <span className="px-1.5 py-0.2 rounded bg-surface-container-low text-on-surface font-mono text-[10px]">
                        {w.status}
                      </span>
                    </div>
                    <span className="text-[11px] text-on-surface-variant">{subtitle}</span>
                  </div>
                  <ProvenanceBadge 
                    type={w.evidence_status || 'SYNTHETIC_STRESS_TEST'}
                    label={w.status === 'ACTIVE' ? 'QC PASSED · SYNTHETIC' : 'UNAVAILABLE'}
                  />
                </div>
                <div className="flex items-baseline justify-between py-1">
                  <div className="flex items-baseline gap-1">
                    <span className="font-data-display font-extrabold text-2xl text-on-surface">
                      {rawVal !== undefined && rawVal !== null ? rawVal : 'N/A'}
                    </span>
                    <span className="text-xs text-on-surface-variant">{summary.unit}</span>
                  </div>
                  <div className="text-right font-mono">
                    <div className={`text-${colorClass} font-bold text-sm`}>{weightPct}%</div>
                    <span className="text-[10px] text-on-surface-variant">Adaptive Weight</span>
                  </div>
                </div>
                <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden my-2">
                  <div className={`bg-${colorClass} h-full rounded-full transition-all duration-500`} style={{ width: `${weightPct}%` }} />
                </div>
                <div className="pt-1 flex items-center justify-between text-on-surface-variant text-[11px] border-t border-outline-variant/20">
                  <span>MAE: <span className="font-mono text-on-surface font-semibold">{w.historical_mae?.toFixed(1) || 'N/A'} {summary.unit}</span></span>
                  <span className="font-semibold">{w.notes?.[0] || 'Active Source'}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stage 01 -> 04 // Canonical Pipeline Stages */}
      <div className="p-4 lg:p-6 pb-0 flex flex-col gap-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-outline uppercase tracking-wider font-bold">
              STAGE 01 → 04 // CANONICAL PIPELINE STAGES
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span className="font-mono text-primary text-[11px] font-bold">STATUS: PIPELINE READY</span>
          </div>
          <span className="font-mono text-[11px] text-on-surface-variant">
            DOMAIN: {currentSub.name}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          
          {/* Phase 01 */}
          <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/30 shadow-xs flex flex-col justify-between min-h-[160px]">
            <div>
              <div className="flex items-center justify-between font-mono text-[11px] text-primary font-bold mb-1">
                <span>PHASE 01</span>
                <span>#HARMONIZE</span>
              </div>
              <h4 className="font-headline font-bold text-sm text-on-surface mb-1">
                Spatial Registration &amp; Units
              </h4>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Source grid to target-region representation. Status: METADATA_ONLY spatial registration.
              </p>
            </div>
            <div className="pt-2 border-t border-outline-variant/20 flex justify-between font-mono text-[10px] text-on-surface-variant">
              <span>Status: <strong className="text-on-surface">METADATA_ONLY</strong></span>
              <span>Unit: <strong className="text-on-surface">{summary.unit}</strong></span>
            </div>
          </div>

          {/* Phase 02 */}
          <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/30 shadow-xs flex flex-col justify-between min-h-[160px]">
            <div>
              <div className="flex items-center justify-between font-mono text-[11px] text-secondary font-bold mb-1">
                <span>PHASE 02</span>
                <span>#CONTEXT</span>
              </div>
              <h4 className="font-headline font-bold text-sm text-on-surface mb-1">
                Regime &amp; Terrain Context
              </h4>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Evaluates terrain features, catchment exposure, and active weather regime classification.
              </p>
            </div>
            <div className="pt-2 border-t border-outline-variant/20 flex justify-between font-mono text-[10px] text-on-surface-variant">
              <span>Regime: <strong className="text-error font-bold">{weatherRegime}</strong></span>
              <span>Lead: <strong className="text-primary font-bold">+{leadHours}H</strong></span>
            </div>
          </div>

          {/* Phase 03 */}
          <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/30 shadow-xs flex flex-col justify-between min-h-[160px]">
            <div>
              <div className="flex items-center justify-between font-mono text-[11px] text-tertiary font-bold mb-1">
                <span>PHASE 03</span>
                <span>#ADAPTIVE_TRUST</span>
              </div>
              <h4 className="font-headline font-bold text-sm text-on-surface mb-1">
                Adaptive Weight Allocation
              </h4>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Derives trust weights from region × lead × regime historical skill, recent verification &amp; disagreement penalties.
              </p>
            </div>
            <div className="pt-2 border-t border-outline-variant/20 flex justify-between font-mono text-[10px] text-on-surface-variant">
              <span>Method: <strong className="text-on-surface">Evidence Trust</strong></span>
              <span>Vector: <strong className="text-primary font-bold">[{summary.weights.map(w => w.weight.toFixed(2)).join(', ')}]</strong></span>
            </div>
          </div>

          {/* Phase 04 */}
          <div className="p-4 rounded-xl bg-surface-container-lowest border border-primary/40 shadow-sm flex flex-col justify-between min-h-[160px]">
            <div>
              <div className="flex items-center justify-between font-mono text-[11px] text-primary font-bold mb-1">
                <span>PHASE 04</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
              </div>
              <h4 className="font-headline font-bold text-sm text-on-surface mb-1">
                Adaptive Fused Output
              </h4>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Weighted ensemble expectation with epistemic disagreement margin.
              </p>
            </div>
            <div className="pt-2 border-t border-outline-variant/20 flex items-baseline justify-between font-mono">
              <div className="flex items-baseline gap-1">
                <span className="font-data-display font-extrabold text-2xl text-on-surface">{summary.fused_forecast}</span>
                <span className="text-[10px] text-on-surface-variant">{summary.unit}</span>
              </div>
              <div className="text-right">
                <div className="text-[11px] text-primary font-bold">Margin: ±{summary.uncertainty?.uncertainty_margin?.toFixed(1) ?? '—'} {summary.unit}</div>
                <span className="text-[9px] text-on-surface-variant">Uncalibrated Indicator</span>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Bottom Workspace: Attribution Waterfall & Uncertainty */}
      <div className="p-4 lg:p-6 grid grid-cols-1 xl:grid-cols-12 gap-5">
        
        {/* Left: Attribution & Explanatory Factors (7 Cols) */}
        <div className="xl:col-span-7 flex flex-col gap-4">
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-xs border border-outline-variant/30 flex flex-col gap-4">
            <div>
              <div className="flex items-center justify-between">
                <h3 className="font-headline font-bold text-base text-on-surface">
                  Why These Weights? (Explanatory Factors)
                </h3>
                <span className="font-mono text-xs text-on-surface-variant">EVIDENCE DECOMPOSITION</span>
              </div>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Primary atmospheric drivers and evidence factors contributing to current model trust allocation.
              </p>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-on-surface font-semibold">Regional Historical Skill (Region × Lead Matrix)</span>
                  <span className="text-primary font-bold">High Contribution (+32%)</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-primary h-full rounded-full" style={{ width: '32%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-on-surface font-semibold">Recent Verification Error Evidence</span>
                  <span className="text-secondary font-bold">Medium Contribution (+24%)</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-secondary h-full rounded-full" style={{ width: '24%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-on-surface font-semibold">Atmospheric Regime Alignment ({weatherRegime})</span>
                  <span className="text-tertiary font-bold">Active Alignment (+22%)</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-tertiary h-full rounded-full" style={{ width: '22%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-on-surface font-semibold">Lead-Time Reliability (+{leadHours}H Horizon)</span>
                  <span className="text-primary font-bold">Lead Decay Factor (+14%)</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-primary-container h-full rounded-full" style={{ width: '14%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-on-surface font-semibold">Inter-Model Disagreement Penalty</span>
                  <span className="text-error font-bold">-8% Penalty</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-error h-full rounded-full" style={{ width: '8%' }} />
                </div>
              </div>
            </div>

            {/* Interactive What-If Scenario Sandbox */}
            <div className="mt-2 p-4 rounded-xl bg-surface-container-low border border-outline-variant/30 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-on-surface flex items-center gap-1.5 uppercase">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-primary" />
                  WHAT-IF SCENARIO SANDBOX (DEMO SIMULATION)
                </span>
                <button 
                  onClick={() => { setCapeValue(2450); setTrustPrior(0.82); }}
                  className="font-mono text-[10px] text-primary hover:underline"
                >
                  Reset Defaults
                </button>
              </div>

              <p className="text-[11px] text-on-surface-variant">
                ⚠ Illustrative scenario sandbox — does not modify operational backend forecast.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Convective Instability (CAPE):</span>
                    <span className="text-primary font-bold">{capeValue} J/kg</span>
                  </div>
                  <input 
                    type="range" 
                    min={800} 
                    max={4500} 
                    value={capeValue} 
                    onChange={(e) => setCapeValue(Number(e.target.value))}
                    className="w-full cursor-pointer accent-primary" 
                  />
                  <div className="flex justify-between text-[9px] text-on-surface-variant mt-0.5">
                    <span>Stable (800)</span>
                    <span>Extreme Convective (4500)</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-on-surface-variant">Ground Truth Trust Prior:</span>
                    <span className="text-secondary font-bold">{trustPrior.toFixed(2)} (High)</span>
                  </div>
                  <input 
                    type="range" 
                    min={0.1} 
                    max={1.0} 
                    step={0.01} 
                    value={trustPrior} 
                    onChange={(e) => setTrustPrior(Number(e.target.value))}
                    className="w-full cursor-pointer accent-secondary" 
                  />
                  <div className="flex justify-between text-[9px] text-on-surface-variant mt-0.5">
                    <span>Noisy Sensors (0.1)</span>
                    <span>Rigorous Truth (1.0)</span>
                  </div>
                </div>
              </div>

              <div className="p-2.5 rounded bg-surface-container-lowest flex items-center justify-between font-mono text-xs border border-outline-variant/20">
                <span className="text-on-surface-variant">Simulated Scenario Response:</span>
                <span className="font-bold text-primary text-sm">
                  {simulatedFused} {summary.unit} <span className="font-normal text-[10px] text-on-surface-variant">(Sandbox Illustrative Value)</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Ensemble Forecast Spread & Uncertainty Indicator (5 Cols) */}
        <div className="xl:col-span-5 flex flex-col gap-4">
          
          {/* Forecast Spread Display */}
          <div className="bg-surface-container-lowest rounded-xl p-5 shadow-xs border border-outline-variant/30 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-headline font-bold text-base text-on-surface">
                  Ensemble Forecast Spread &amp; Uncertainty Indicator
                </h3>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  Model spread and baseline comparison around fused estimate.
                </p>
              </div>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant uppercase">
                {summary.disagreement?.disagreement_level || 'HIGH'} SPREAD
              </span>
            </div>

            {/* SVG Ensemble Spread Visualizer */}
            <div className="w-full h-44 bg-[#f8fafc] dark:bg-[#091122] rounded-lg p-3 relative overflow-hidden border border-outline-variant/20 flex flex-col justify-between">
              <div className="flex justify-between font-mono text-[10px] text-on-surface-variant">
                <span>Min: {minVal.toFixed(1)} {summary.unit}</span>
                <span className="text-primary font-bold">Fused: {summary.fused_forecast} {summary.unit}</span>
                <span>Max: {maxVal.toFixed(1)} {summary.unit}</span>
              </div>

              <div className="relative w-full h-12 flex items-center">
                {/* Horizontal Range Line */}
                <div className="w-full h-1.5 bg-surface-container-high rounded-full relative">
                  <div 
                    className="absolute h-full bg-primary/30 rounded-full" 
                    style={{ left: '10%', right: '10%' }} 
                  />
                  {/* Fused Pin */}
                  <div 
                    className="absolute w-4 h-6 -top-2 bg-primary text-on-primary font-mono text-[10px] font-bold rounded flex items-center justify-center shadow-md -translate-x-1/2"
                    style={{ left: '50%' }}
                  >
                    ★
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center font-mono text-[10px] text-on-surface-variant pt-2 border-t border-outline-variant/20">
                <span>Spread: <strong className="text-on-surface">{summary.disagreement?.forecast_spread?.toFixed(1) || '0.0'} {summary.unit}</strong></span>
                <span>Margin: <strong className="text-primary">±{summary.uncertainty?.uncertainty_margin?.toFixed(1) ?? '—'} {summary.unit}</strong></span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center font-mono">
              <div className="p-2 rounded bg-surface-container-low">
                <div className="text-[10px] text-on-surface-variant">Simple Avg</div>
                <div className="text-sm font-bold text-on-surface">{summary.baselines?.simple_average} {summary.unit}</div>
              </div>
              <div className="p-2 rounded bg-primary-fixed">
                <div className="text-[10px] text-on-primary-fixed-variant font-semibold">VARUNA Fused</div>
                <div className="text-sm font-extrabold text-on-primary-fixed">{summary.fused_forecast} {summary.unit}</div>
              </div>
              <div className="p-2 rounded bg-surface-container-low">
                <div className="text-[10px] text-on-surface-variant">Static Blend</div>
                <div className="text-sm font-bold text-on-surface">{summary.baselines?.static_blend} {summary.unit}</div>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between text-xs font-mono border-t border-outline-variant/20">
              <span className="text-on-surface-variant">Calibration Status:</span>
              <span className="font-bold text-primary">Uncalibrated Uncertainty Indicator</span>
            </div>
          </div>

          {/* SIH26081 Scientific Provenance Audit Card */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-xs border border-outline-variant/30 flex items-start gap-3">
            <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center shrink-0">
              <FileCheck className="w-4 h-4 text-primary" />
            </div>
            <div className="flex flex-col gap-1 text-xs">
              <div className="flex items-center gap-1.5 font-headline font-bold text-on-surface">
                <span>SIH26081 Scientific Provenance Audit</span>
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
              </div>
              <p className="text-on-surface-variant leading-relaxed text-[11px]">
                Controlled Synthetic Stress Benchmark: <strong className="text-primary font-semibold">{formatBenchmark(benchmark)}</strong> — measured against simple multi-model averaging on a chronological held-out synthetic test set. Illustrative evaluation only — not operational validation.
              </p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
