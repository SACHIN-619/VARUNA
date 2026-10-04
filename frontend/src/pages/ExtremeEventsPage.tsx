import React, { useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { ExtremeEventItem } from '../types';
import { AlertTriangle, ShieldAlert, CheckCircle2, ChevronRight, X } from 'lucide-react';

export const ExtremeEventsPage: React.FC = () => {
  const { subdivisions } = useVaruna();

  const events: ExtremeEventItem[] = [
    {
      id: 'EVT-01',
      region: 'IN_TELANGANA_DECCAN',
      region_name: 'Telangana (Deccan Catchment)',
      event: 'Heavy Convective Rainfall Burst',
      risk_signal: 'HIGH',
      confidence: 'MEDIUM',
      forecast_window: '24–48 Hours',
      model_consensus: 'Moderate',
      model_disagreement: 'HIGH',
      supporting_models: ['NCUM (82mm)', 'WRF (47mm)', 'AI Weather (64mm)'],
      contradicting_signal: 'GFS predicts extreme outlier at 103mm (severe wet-bias suspected)',
      varuna_interpretation: 'Fused value 70.1 mm indicates high risk of urban inundation in Hyderabad metropolitan core. Confidence is graded MEDIUM due to high inter-model spread.'
    },
    {
      id: 'EVT-02',
      region: 'IN_ODISHA_COAST',
      region_name: 'Odisha Coastal Corridor',
      event: 'Bay of Bengal Depression Landfall Convergence',
      risk_signal: 'CRITICAL',
      confidence: 'MEDIUM',
      forecast_window: '36–60 Hours',
      model_consensus: 'Low',
      model_disagreement: 'HIGH',
      supporting_models: ['NCUM (95mm)', 'AI Weather (88mm)'],
      contradicting_signal: 'WRF 3km predicts coastal landfall diversion northward',
      varuna_interpretation: 'Severe spread across coastal catchments. Clamped GFS contribution. Continuous radar assimilation recommended.'
    },
    {
      id: 'EVT-03',
      region: 'IN_WESTERN_GHATS_KERALA',
      region_name: 'Kerala & Western Ghats',
      event: 'Orographic Monsoon Torrent / Landslide Risk',
      risk_signal: 'ELEVATED',
      confidence: 'HIGH',
      forecast_window: '24–48 Hours',
      model_consensus: 'High',
      model_disagreement: 'LOW',
      supporting_models: ['WRF (88mm)', 'NCUM (82mm)', 'AI Weather (76mm)'],
      contradicting_signal: 'None. Strong multi-model orographic convergence.',
      varuna_interpretation: 'High confidence consensus. Orographic lifting bonus granted to WRF 3km. Elevated slope saturation signal.'
    },
    {
      id: 'EVT-04',
      region: 'IN_ASSAM_MEGHALAYA',
      region_name: 'Assam & Meghalaya Valley',
      event: 'Brahmaputra Riverine Basin Cloudburst Risk',
      risk_signal: 'ELEVATED',
      confidence: 'MEDIUM',
      forecast_window: '48–72 Hours',
      model_consensus: 'Moderate',
      model_disagreement: 'MEDIUM',
      supporting_models: ['NCUM (110mm)', 'WRF (98mm)'],
      contradicting_signal: 'AI Weather predicts lower peak volume (74mm)',
      varuna_interpretation: 'Catchment inflow indices approaching threshold. Secondary advisory recommended.'
    }
  ];

  const [selectedEvent, setSelectedEvent] = useState<ExtremeEventItem | null>(events[0]);

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-rose-600 dark:text-rose-400 font-bold uppercase tracking-wider">
              Decision-Support Extreme Weather Intelligence
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="DECISION SUPPORT PROTOTYPE" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            EXTREME EVENT RISK MATRIX
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Calibrated anomaly detection evaluating model consensus against IMD extreme thresholds (Heavy ≥ 64.5mm).
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-on-surface-variant">
          <span className="px-2.5 py-1 rounded bg-rose-50 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 border border-rose-700 font-bold">
            ● 4 SUBDIVISIONS FLAGGED
          </span>
        </div>
      </div>

      {/* Main Grid: Event Matrix & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Table / Matrix (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-3">
          <div className="rounded-xl bg-surface border border-surface-border overflow-hidden shadow-lg">
            <div className="p-3.5 bg-surface-deep border-b border-surface-border flex items-center justify-between text-xs font-mono text-on-surface-variant">
              <span>METEOROLOGICAL EVENT MATRIX</span>
              <span>ACTIONS</span>
            </div>

            <div className="divide-y divide-surface-border">
              {events.map((evt) => {
                const isSelected = selectedEvent?.id === evt.id;
                const isCritical = evt.risk_signal === 'CRITICAL' || evt.risk_signal === 'HIGH';

                return (
                  <div
                    key={evt.id}
                    onClick={() => setSelectedEvent(evt)}
                    className={`p-4 transition-colors cursor-pointer flex items-center justify-between ${
                      isSelected ? 'bg-cyan-50 dark:bg-cyan-950/40 border-l-4 border-cyan-400' : 'hover:bg-surface-card'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${isCritical ? 'bg-rose-500' : 'bg-amber-400'}`} />
                        <span className="font-headline font-bold text-sm text-on-surface">{evt.region_name}</span>
                        <span className={`text-[10px] font-mono px-2 py-0.2 rounded border font-bold ${
                          evt.risk_signal === 'CRITICAL' 
                            ? 'bg-rose-50 dark:bg-rose-950 text-rose-600 dark:text-rose-400 border-rose-800' 
                            : 'bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400 border-amber-800'
                        }`}>
                          {evt.risk_signal}
                        </span>
                      </div>
                      <div className="text-xs font-mono text-on-surface-variant">{evt.event}</div>
                      <div className="text-[10px] font-mono text-slate-500">
                        Horizon: {evt.forecast_window} • Confidence: <strong className="text-on-surface-variant">{evt.confidence}</strong>
                      </div>
                    </div>

                    <ChevronRight className={`w-5 h-5 transition-transform ${isSelected ? 'text-primary translate-x-1' : 'text-slate-600'}`} />
                  </div>
                );
              })}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-surface-deep border border-surface-border text-xs font-mono text-on-surface-variant flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong>Institutional Disclaimer:</strong> VARUNA is a decision-support research prototype. 
              Official meteorological bulletins and autonomous public warnings remain under the statutory authority of the India Meteorological Department (IMD / MoES).
            </div>
          </div>
        </div>

        {/* Right Event Intelligence Card (5 cols) */}
        <div className="lg:col-span-5">
          {selectedEvent ? (
            <div className="p-5 rounded-xl bg-surface border border-surface-border flex flex-col gap-4 shadow-xl">
              <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                <span className="text-xs font-mono text-primary uppercase font-semibold">
                  EVENT INTELLIGENCE DOSSIER
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface-card text-on-surface-variant border border-surface-border">
                  {selectedEvent.id}
                </span>
              </div>

              <div>
                <h3 className="font-headline font-extrabold text-lg text-on-surface">
                  {selectedEvent.event}
                </h3>
                <span className="text-xs font-mono text-on-surface-variant">
                  Target Zone: {selectedEvent.region_name}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded bg-surface-deep border border-surface-border">
                  <span className="text-slate-500 text-[10px] uppercase block">Window</span>
                  <span className="font-bold text-on-surface">{selectedEvent.forecast_window}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-deep border border-surface-border">
                  <span className="text-slate-500 text-[10px] uppercase block">Confidence</span>
                  <span className="font-bold text-amber-600 dark:text-amber-400">{selectedEvent.confidence}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-deep border border-surface-border">
                  <span className="text-slate-500 text-[10px] uppercase block">Consensus</span>
                  <span className="font-bold text-on-surface">{selectedEvent.model_consensus}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-deep border border-surface-border">
                  <span className="text-slate-500 text-[10px] uppercase block">Disagreement</span>
                  <span className="font-bold text-rose-600 dark:text-rose-400">{selectedEvent.model_disagreement}</span>
                </div>
              </div>

              {/* Supporting and Contradicting Models */}
              <div className="space-y-2 text-xs font-mono">
                <div className="p-3 rounded bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-600/30">
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold block mb-1">Supporting Models:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedEvent.supporting_models.map(m => (
                      <span key={m} className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 border border-emerald-800 text-[11px]">
                        {m}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded bg-amber-50 dark:bg-amber-950/30 border border-amber-600/30">
                  <span className="text-amber-600 dark:text-amber-400 font-bold block mb-1">Contradicting Signal:</span>
                  <span className="text-on-surface-variant text-[11px] leading-relaxed block">
                    {selectedEvent.contradicting_signal}
                  </span>
                </div>
              </div>

              {/* VARUNA Interpretation */}
              <div className="p-3.5 rounded-lg bg-surface-deep border border-cyan-500/30 text-xs font-body text-on-surface leading-relaxed">
                <strong className="text-primary block mb-1 font-headline">VARUNA Decision Support Guidance:</strong>
                {selectedEvent.varuna_interpretation}
              </div>
            </div>
          ) : (
            <div className="p-8 rounded-xl bg-surface border border-surface-border text-center text-slate-500 font-mono text-xs">
              Select an extreme event from the matrix to inspect intelligence details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
