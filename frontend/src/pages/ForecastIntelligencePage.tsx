import React from 'react';
import { useVaruna } from '../context/VarunaContext';
import { IndiaMetMap } from '../components/maps/IndiaMetMap';
import { ModelTrustBars } from '../components/shared/ModelTrustBars';
import { ModelConsensusPanel } from '../components/shared/ModelConsensusPanel';
import { DisagreementMeter } from '../components/shared/DisagreementMeter';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { CloudRain, Sparkles, AlertCircle, ArrowUpRight, Clock, HelpCircle } from 'lucide-react';

export const ForecastIntelligencePage: React.FC = () => {
  const { summary, regionId, subdivisions, leadHours, variable, weatherRegime, setActiveRoute } = useVaruna();
  const currentSub = (subdivisions && subdivisions.find(s => s.id === regionId)) || (subdivisions && subdivisions[0]) || {
    id: regionId || 'IN_TELANGANA_HYDERABAD',
    name: 'Telangana (Deccan Basin)',
    terrain: 'Plateau Orography',
    state: 'Telangana',
    climatic_zone: 'Semi-Arid Transition',
    risk_profile: 'Urban Inundation',
    centroid: { lat: 17.385, lon: 78.4867 },
    bbox: [77.2, 15.8, 81.3, 19.9],
    dominant_model: 'NCUM',
    trust_percentage: 46,
    weights: { NCUM: 0.46, WRF: 0.31, AI_WEATHER: 0.18, GFS: 0.05 },
    disagreement_level: 'HIGH',
    rainfall_mm: 70.1,
    confidence: 'MEDIUM'
  };

  const probVal = summary?.uncertainty?.probability ?? 78.4;
  const activeCycle = summary?.active_cycle || '2026-09-28 00:00 UTC';
  const fusedVal = summary?.fused_forecast ?? 70.1;
  const unitVal = summary?.unit || (variable === 'rainfall' ? 'mm' : variable === 'temperature' ? '°C' : 'km/h');

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider">
              Meteorological Operations Centre
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="SUPERVISED ADAPTIVE ML" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            FORECAST INTELLIGENCE CENTRE
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Continuous multi-model trust evaluation, adaptive weighting, and epistemic uncertainty quantification.
          </p>
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="p-2.5 rounded-lg bg-surface border border-surface-border flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-on-surface-variant">STATUS:</span>
            <strong className="text-on-surface">CALCULATED</strong>
          </div>
          <div className="p-2.5 rounded-lg bg-surface border border-surface-border flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            <span className="text-on-surface-variant">CYCLE:</span>
            <strong className="text-primary">{activeCycle}</strong>
          </div>
        </div>
      </div>

      {/* Hero Forecast Banner */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8">
          <ModelConsensusPanel
            modelForecasts={summary?.model_forecasts || {}}
            fusedValue={fusedVal}
            baselines={summary?.baselines || { simple_average: 74.0, static_blend: 71.5 }}
            unit={unitVal}
          />
        </div>

        <div className="lg:col-span-4 p-5 rounded-xl bg-surface border border-surface-border flex flex-col justify-between">
          <div>
            <div className="text-xs font-mono text-on-surface-variant uppercase tracking-wider mb-1">
              Active Focus Subdivision
            </div>
            <div className="font-headline font-bold text-xl text-on-surface">
              {currentSub.name}
            </div>
            <div className="text-xs font-mono text-primary mt-0.5">
              Terrain: {currentSub.terrain}
            </div>
          </div>

          <div className="space-y-2 my-4 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-surface-border/60">
              <span className="text-on-surface-variant">Horizon:</span>
              <span className="font-bold text-on-surface">+{leadHours} Hours</span>
            </div>
            <div className="flex justify-between py-1 border-b border-surface-border/60">
              <span className="text-on-surface-variant">Weather Regime:</span>
              <span className="font-bold text-amber-600 dark:text-amber-400">{weatherRegime}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-on-surface-variant">Event Probability:</span>
              <span className="font-bold text-primary">{typeof probVal === 'number' ? probVal.toFixed(1) : probVal}%</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveRoute('why-this-forecast')}
              className="flex-1 py-2 rounded-lg bg-surface-card hover:bg-surface-cardHover text-primary font-mono text-xs border border-surface-border font-semibold flex items-center justify-center gap-1 transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Why {fusedVal.toFixed(1)} {unitVal}?</span>
            </button>
            <button
              onClick={() => setActiveRoute('what-changed')}
              className="flex-1 py-2 rounded-lg bg-surface-card hover:bg-surface-cardHover text-on-surface-variant font-mono text-xs border border-surface-border font-semibold flex items-center justify-center gap-1 transition-colors"
            >
              <Clock className="w-3.5 h-3.5" />
              <span>What Changed?</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Trust Bars, Disagreement & Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-5 flex flex-col gap-5">
          <div className="p-4 rounded-xl bg-surface border border-surface-border">
            <h3 className="font-headline font-bold text-sm text-on-surface mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              ADAPTIVE MODEL TRUST BREAKDOWN
            </h3>
            <ModelTrustBars weights={summary?.weights || []} />
          </div>

          <DisagreementMeter
            disagreement={summary?.disagreement || { disagreement_level: 'HIGH', disagreement_score: 0.812, forecast_spread: 23.8, weighted_spread: 21.2, range: 56.0, variance: 566.4 }}
            uncertainty={summary?.uncertainty || { confidence: 'MEDIUM', confidence_score: 0.642, probability: 78.4, hazard_exceedance_indicator_pct: 78.4, uncertainty_margin: 28.5, threshold: 64.5, lower_bound: 48.0, upper_bound: 96.0, calibrated: false }}
            modelValues={summary?.model_forecasts || {}}
            fusedValue={fusedVal}
          />
        </div>

        <div className="lg:col-span-7 flex flex-col gap-4">
          <IndiaMetMap heightClass="h-[560px]" />
        </div>
      </div>
    </div>
  );
};
