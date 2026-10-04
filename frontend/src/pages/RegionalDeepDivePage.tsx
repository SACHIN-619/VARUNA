import React from 'react';
import { useVaruna } from '../context/VarunaContext';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { Compass, MapPin, TrendingUp, Sparkles, Layers, Clock } from 'lucide-react';
import { IndiaMetMap } from '../components/maps/IndiaMetMap';

export const RegionalDeepDivePage: React.FC = () => {
  const { summary, regionId, setRegionId, subdivisions, leadHours, variable, setLeadHours } = useVaruna();
  const currentSub = subdivisions.find(s => s.id === regionId) || subdivisions[0];

  // Timeline mock simulation for 24h, 48h, 72h
  const timelineData = [
    {
      lead: 24,
      fused: variable === 'rainfall' ? 42.5 : 29.8,
      ncum: variable === 'rainfall' ? 48.0 : 30.0,
      wrf: variable === 'rainfall' ? 52.0 : 29.2,
      ai: variable === 'rainfall' ? 38.0 : 30.1,
      gfs: variable === 'rainfall' ? 62.0 : 31.4,
      dominant: "WRF",
      dominantTrust: "48%"
    },
    {
      lead: 48,
      fused: summary.fused_forecast,
      ncum: summary.model_forecasts.NCUM,
      wrf: summary.model_forecasts.WRF,
      ai: summary.model_forecasts.AI_WEATHER,
      gfs: summary.model_forecasts.GFS,
      dominant: summary.explanation.dominant_model,
      dominantTrust: "46%"
    },
    {
      lead: 72,
      fused: variable === 'rainfall' ? 28.0 : 32.5,
      ncum: variable === 'rainfall' ? 34.0 : 32.0,
      wrf: variable === 'rainfall' ? 18.0 : 33.2,
      ai: variable === 'rainfall' ? 31.0 : 32.2,
      gfs: variable === 'rainfall' ? 55.0 : 34.0,
      dominant: "AI_WEATHER",
      dominantTrust: "52%"
    }
  ];

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider">
              Geographic Subdivision Deep-Dive
            </span>
            <ProvenanceBadge type="PHYSICS_INFORMED_HEURISTIC" label="SUBDIVISION LOCALIZED RUN" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            {currentSub.name}
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            State: {currentSub.state} • Terrain: {currentSub.terrain} • Climatic Zone: {currentSub.climatic_zone}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={regionId}
            onChange={(e) => setRegionId(e.target.value)}
            className="bg-surface border border-surface-border text-on-surface text-xs font-mono rounded px-3 py-1.5 cursor-pointer focus:outline-none"
          >
            {subdivisions.map(s => (
              <option key={s.id} value={s.id} className="bg-surface-deep">
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Left Details & Right Geospatial View */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
        <div className="xl:col-span-4 flex flex-col gap-4">
          <div className="p-5 rounded-xl bg-surface border border-surface-border flex flex-col gap-4">
            <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
              Regional Synthesis
            </h3>

            <div className="p-4 rounded-xl bg-surface-deep border border-cyan-500/40">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase">
                Active Fused Precipitation ({leadHours}H)
              </span>
              <div className="font-mono text-4xl font-black text-primary mt-1">
                {summary.fused_forecast.toFixed(1)} <span className="text-sm font-normal text-on-surface-variant">{summary.unit}</span>
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs font-mono">
                <span className="text-on-surface-variant">Confidence:</span>
                <span className="text-amber-600 dark:text-amber-400 font-bold">{summary.uncertainty.confidence}</span>
              </div>
            </div>

            <div className="space-y-2 text-xs font-mono text-on-surface-variant">
              <div className="flex justify-between py-1 border-b border-surface-border">
                <span className="text-on-surface-variant">Dominant Model:</span>
                <span className="font-bold text-primary">{summary.explanation.dominant_model} (46%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-surface-border">
                <span className="text-on-surface-variant">Model Spread:</span>
                <span className="font-bold text-amber-600 dark:text-amber-400">±{summary.disagreement.forecast_spread.toFixed(1)} mm</span>
              </div>
              <div className="flex justify-between py-1 border-b border-surface-border">
                <span className="text-on-surface-variant">Risk Profile:</span>
                <span className="text-on-surface">{currentSub.risk_profile}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-on-surface-variant">GIS Centroid:</span>
                <span className="text-on-surface">{currentSub.centroid.lat.toFixed(2)}°N, {currentSub.centroid.lon.toFixed(2)}°E</span>
              </div>
            </div>
          </div>
        </div>

        <div className="xl:col-span-8 flex flex-col gap-4">
          <IndiaMetMap heightClass="h-[480px]" showControls={false} />
        </div>
      </div>

      {/* Forecast Timeline Horizon: 24h -> 48h -> 72h */}
      <div className="p-5 rounded-xl bg-surface border border-surface-border flex flex-col gap-4">
        <div className="flex items-center justify-between pb-2 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider">
              Lead Time Horizon Comparison (24H ── 48H ── 72H)
            </h3>
          </div>
          <span className="text-xs font-mono text-on-surface-variant">
            Note how dominant model trust shifts from WRF (24h) to NCUM (48h) to AI Weather (72h)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {timelineData.map((t) => (
            <div
              key={t.lead}
              onClick={() => setLeadHours(t.lead as any)}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                leadHours === t.lead
                  ? 'bg-cyan-50 dark:bg-cyan-950/40 border-cyan-500 shadow-glow-cyan/20'
                  : 'bg-surface-deep border-surface-border hover:border-outline-variant'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-headline font-extrabold text-base text-on-surface">
                  +{t.lead} Hours
                </span>
                {leadHours === t.lead && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-50 dark:bg-cyan-950 text-primary border border-cyan-700">
                    ACTIVE
                  </span>
                )}
              </div>

              <div className="font-mono text-3xl font-extrabold text-primary mb-3">
                {t.fused.toFixed(1)} <span className="text-xs font-normal text-on-surface-variant">{summary.unit}</span>
              </div>

              <div className="space-y-1 font-mono text-xs text-on-surface-variant border-t border-surface-border pt-2">
                <div className="flex justify-between"><span>NCUM:</span> <strong>{t.ncum.toFixed(1)} mm</strong></div>
                <div className="flex justify-between"><span>WRF:</span> <strong>{t.wrf.toFixed(1)} mm</strong></div>
                <div className="flex justify-between"><span>AI:</span> <strong>{t.ai.toFixed(1)} mm</strong></div>
                <div className="flex justify-between"><span>GFS:</span> <strong>{t.gfs.toFixed(1)} mm</strong></div>
              </div>

              <div className="mt-3 pt-2 border-t border-surface-border flex justify-between text-[11px] font-mono">
                <span className="text-on-surface-variant">Dominant:</span>
                <span className="text-primary font-bold">{t.dominant} ({t.dominantTrust})</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
