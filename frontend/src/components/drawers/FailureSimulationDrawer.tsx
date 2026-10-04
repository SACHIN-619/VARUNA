import React, { useState } from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { injectFailure, resetFailureOverrides } from '../../services/api';
import { X, AlertOctagon, RotateCcw, ShieldCheck, Zap, AlertTriangle } from 'lucide-react';
import { ProvenanceBadge } from '../shared/ProvenanceBadge';

export const FailureSimulationDrawer: React.FC = () => {
  const { 
    isFailureModalOpen, 
    setIsFailureModalOpen, 
    setSimulatedDisabledModel, 
    simulatedDisabledModel,
    refreshData 
  } = useVaruna();

  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  if (!isFailureModalOpen) return null;

  const handleSimulateDropout = async (modelId: 'WRF' | 'GFS' | 'AI_WEATHER' | 'NCUM') => {
    setLoadingAction(modelId);
    try {
      await injectFailure('simulate_missing_model', modelId);
      setSimulatedDisabledModel(modelId);
      setStatusMessage(`Model ${modelId} marked UNAVAILABLE. Dynamic simplex engine re-normalized remaining weights.`);
      await refreshData();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleInjectBias = async () => {
    setLoadingAction('bias');
    try {
      await injectFailure('simulate_model_bias', 'GFS', 35.0);
      setStatusMessage('Injected +35mm operational wet-bias into GFS. Recent bias penalty increased.');
      await refreshData();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleForceDisagreement = async () => {
    setLoadingAction('disagree');
    try {
      await injectFailure('simulate_disagreement');
      setStatusMessage('Multi-model divergence forced. Forecast spread escalated; confidence downgraded.');
      await refreshData();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleReset = async () => {
    setLoadingAction('reset');
    try {
      await resetFailureOverrides();
      setSimulatedDisabledModel(null);
      setStatusMessage('All runtime failure injections cleared. Nominal operational state restored.');
      await refreshData();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div className="w-full max-w-lg bg-surface-container-lowest border-l border-outline-variant/30 h-full overflow-y-auto p-6 flex flex-col justify-between shadow-2xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-5 h-5 text-amber-500" />
              <div>
                <h3 className="font-headline font-bold text-base text-on-surface">
                  OPERATIONAL FAILURE SIMULATOR
                </h3>
                <span className="text-[11px] font-mono text-amber-600 font-semibold">
                  SIH26081 Resilience & Graceful Degradation Demo
                </span>
              </div>
            </div>
            <button
              onClick={() => setIsFailureModalOpen(false)}
              className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <ProvenanceBadge type="SYNTHETIC_STRESS_TEST" label="SIMULATION SCENARIOS ONLY" />

          {/* Explanation Banner */}
          <div className="p-3.5 rounded-lg bg-surface-container-low border border-outline-variant/30 text-xs text-on-surface leading-relaxed font-body">
            This module proves that VARUNA does not blindly crash when a numerical weather model drops out or exhibits anomalous bias. 
            Simulate feed interruptions and watch VARUNA dynamically rebalance trust weights to ensure continuous decision support.
          </div>

          {statusMessage && (
            <div className="p-3 rounded bg-primary/10 border border-primary/30 text-xs font-mono text-primary font-semibold animate-fadeIn">
              <strong>Engine Telemetry:</strong> {statusMessage}
            </div>
          )}

          {/* Action 1: Model Dropouts */}
          <div className="space-y-3">
            <h4 className="font-headline font-semibold text-xs text-on-surface-variant uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-primary" />
              1. Simulate Model Source Dropout
            </h4>
            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              <button
                onClick={() => handleSimulateDropout('WRF')}
                disabled={loadingAction !== null}
                className={`p-3 rounded-lg border text-left transition-all ${
                  simulatedDisabledModel === 'WRF'
                    ? 'bg-rose-500/10 border-rose-500 text-rose-700 font-bold'
                    : 'bg-surface-container-low hover:bg-surface-container-high border-outline-variant/30 text-on-surface'
                }`}
              >
                <div className="font-bold flex items-center justify-between">
                  <span>Drop WRF (3km)</span>
                  {simulatedDisabledModel === 'WRF' && <span className="text-[9px] text-rose-600 font-bold">OFFLINE</span>}
                </div>
                <div className="text-[10px] text-on-surface-variant mt-1">Rebalances to NCUM 63%, AI 25%, GFS 12%</div>
              </button>

              <button
                onClick={() => handleSimulateDropout('GFS')}
                disabled={loadingAction !== null}
                className={`p-3 rounded-lg border text-left transition-all ${
                  simulatedDisabledModel === 'GFS'
                    ? 'bg-rose-500/10 border-rose-500 text-rose-700 font-bold'
                    : 'bg-surface-container-low hover:bg-surface-container-high border-outline-variant/30 text-on-surface'
                }`}
              >
                <div className="font-bold flex items-center justify-between">
                  <span>Drop GFS (25km)</span>
                  {simulatedDisabledModel === 'GFS' && <span className="text-[9px] text-rose-600 font-bold">OFFLINE</span>}
                </div>
                <div className="text-[10px] text-on-surface-variant mt-1">Isolates regional NWP & AI models</div>
              </button>
            </div>
          </div>

          {/* Action 2: Model Bias Injection */}
          <div className="space-y-3">
            <h4 className="font-headline font-semibold text-xs text-on-surface-variant uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              2. Inject Severe Model Bias
            </h4>
            <button
              onClick={handleInjectBias}
              disabled={loadingAction !== null}
              className="w-full p-3 rounded-lg bg-surface-container-low hover:bg-surface-container-high border border-outline-variant/30 text-left font-mono text-xs transition-colors"
            >
              <div className="font-bold text-on-surface flex items-center justify-between">
                <span>Inject +35 mm GFS Wet Bias</span>
                <span className="text-[10px] text-amber-600 font-bold">Vulnerability Stress</span>
              </div>
              <div className="text-[10px] text-on-surface-variant mt-1">
                Triggers rolling EMA verification penalty and dampens GFS weight toward zero.
              </div>
            </button>
          </div>

          {/* Action 3: Disagreement escalation */}
          <div className="space-y-3">
            <h4 className="font-headline font-semibold text-xs text-on-surface-variant uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              3. Force Ensemble Divergence
            </h4>
            <button
              onClick={handleForceDisagreement}
              disabled={loadingAction !== null}
              className="w-full p-3 rounded-lg bg-surface-container-low hover:bg-surface-container-high border border-outline-variant/30 text-left font-mono text-xs transition-colors"
            >
              <div className="font-bold text-on-surface flex items-center justify-between">
                <span>Widen Multi-Model Spread</span>
                <span className="text-[10px] text-amber-600 font-bold">Epistemic Uncertainty</span>
              </div>
              <div className="text-[10px] text-on-surface-variant mt-1">
                Drives spread from ±23mm to ±65mm. Automatically drops confidence to LOW.
              </div>
            </button>
          </div>
        </div>

        {/* Reset / Restore Nominal button */}
        <div className="pt-6 border-t border-outline-variant/30 space-y-2">
          <button
            onClick={handleReset}
            disabled={loadingAction !== null}
            className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-headline font-bold text-xs uppercase tracking-wide transition-all shadow-xs flex items-center justify-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset to Nominal Operational State</span>
          </button>
          <div className="text-center text-[10px] font-mono text-on-surface-variant">
            Clears all temporary overrides and re-synchronizes with canonical baseline.
          </div>
        </div>
      </div>
    </div>
  );
};
