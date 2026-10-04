import React from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { X, MapPin, ArrowUpRight, TrendingUp, TrendingDown, ExternalLink } from 'lucide-react';
import { ProvenanceBadge } from '../shared/ProvenanceBadge';

export const RegionDetailDrawer: React.FC = () => {
  const { selectedSubdivision, setSelectedSubdivision, setActiveRoute } = useVaruna();

  if (!selectedSubdivision) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div className="w-full max-w-md bg-surface-container-lowest border-l border-outline-variant/30 h-full overflow-y-auto p-6 flex flex-col justify-between shadow-2xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30">
            <div className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-primary" />
              <div>
                <h3 className="font-headline font-bold text-base text-on-surface">
                  {selectedSubdivision.name}
                </h3>
                <span className="text-[11px] font-mono text-on-surface-variant">
                  State: {selectedSubdivision.state} • {selectedSubdivision.climatic_zone}
                </span>
              </div>
            </div>
            <button
              onClick={() => setSelectedSubdivision(null)}
              className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <ProvenanceBadge type="PHYSICS_INFORMED_HEURISTIC" label="SUBDIVISION HEURISTIC PROFILE" />

          {/* Fused Forecast Card */}
          <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/30 flex items-center justify-between shadow-xs">
            <div>
              <span className="text-[10px] font-mono text-on-surface-variant uppercase tracking-wider">
                Fused 48H Rainfall
              </span>
              <div className="font-mono text-3xl font-extrabold text-primary">
                {selectedSubdivision.rainfall_mm ?? 70.1} <span className="text-sm font-normal text-on-surface-variant">mm</span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase">Confidence</span>
              <div className="text-xs font-mono font-bold text-amber-600">
                {selectedSubdivision.confidence ?? 'MEDIUM'}
              </div>
            </div>
          </div>

          {/* Model Trust Distribution */}
          <div className="space-y-3">
            <h4 className="font-headline font-semibold text-xs text-on-surface-variant uppercase tracking-wider">
              Assigned Model Trust Weights
            </h4>
            <div className="space-y-2">
              {Object.entries(selectedSubdivision.weights || { NCUM: 0.46, WRF: 0.31, AI_WEATHER: 0.18, GFS: 0.05 }).map(([m, wt]) => (
                <div key={m} className="p-2.5 rounded bg-surface-container-low border border-outline-variant/30 flex items-center justify-between font-mono text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-on-surface">{m}</span>
                    {m === selectedSubdivision.dominant_model && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-primary-container text-on-primary-container font-bold">
                        Dominant
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-on-surface">{Math.round(wt * 100)}%</span>
                    <span className="text-on-surface-variant">({wt.toFixed(2)})</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Disagreement and Recent Drift */}
          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 rounded bg-surface-container-low border border-outline-variant/30">
              <span className="text-on-surface-variant block text-[10px] uppercase">Disagreement</span>
              <span className={`font-bold text-sm ${selectedSubdivision.disagreement_level === 'HIGH' ? 'text-amber-600' : 'text-emerald-600'}`}>
                {selectedSubdivision.disagreement_level || 'HIGH'}
              </span>
            </div>

            <div className="p-3 rounded bg-surface-container-low border border-outline-variant/30">
              <span className="text-on-surface-variant block text-[10px] uppercase">Recent Drift</span>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-emerald-600 flex items-center text-xs font-bold">
                  NCUM <TrendingUp className="w-3 h-3 ml-0.5" />
                </span>
                <span className="text-rose-600 flex items-center text-xs font-bold">
                  WRF <TrendingDown className="w-3 h-3 ml-0.5" />
                </span>
              </div>
            </div>
          </div>

          {/* Terrain & Risk profile */}
          <div className="p-3 rounded bg-surface-container-low border border-outline-variant/30 text-xs space-y-1.5 font-mono text-on-surface">
            <div><strong>Terrain:</strong> {selectedSubdivision.terrain}</div>
            <div><strong>Risk Profile:</strong> {selectedSubdivision.risk_profile}</div>
            <div><strong>Coordinates:</strong> {selectedSubdivision.centroid.lat.toFixed(2)}°N, {selectedSubdivision.centroid.lon.toFixed(2)}°E</div>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-6 border-t border-outline-variant/30">
          <button
            onClick={() => {
              setSelectedSubdivision(null);
              setActiveRoute('regional');
            }}
            className="w-full py-2.5 rounded-lg bg-primary hover:bg-primary/90 text-on-primary font-headline font-bold text-xs uppercase tracking-wide transition-all shadow-xs flex items-center justify-center gap-2"
          >
            <span>Open Regional Deep-Dive</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
