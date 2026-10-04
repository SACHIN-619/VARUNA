import React, { useState } from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { X, ChevronRight, ChevronLeft, Play, Sparkles, CheckCircle2, RotateCcw } from 'lucide-react';
import { ProvenanceBadge } from './ProvenanceBadge';

interface DemoStep {
  step: number;
  title: string;
  subtitle: string;
  description: string;
  concept: string;
  actionText?: string;
  action?: () => void;
}

export const InteractiveDemoModal: React.FC = () => {
  const { 
    isDemoModalOpen, 
    setIsDemoModalOpen, 
    setActiveRoute, 
    setSimulatedDisabledModel, 
    refreshData 
  } = useVaruna();

  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);

  if (!isDemoModalOpen) return null;

  const steps: DemoStep[] = [
    {
      step: 1,
      title: "Step 1: Heterogeneous NWP & AI Weather Feeds",
      subtitle: "The Operational Reality Over India",
      description: "India has world-class numerical models (NCUM 12km, WRF 3km, GFS 25km, AI Weather 0.25°). In this 48h forecast cycle over Telangana, raw predictions wildly diverge: WRF predicts 47.0 mm, AI predicts 64.0 mm, NCUM predicts 82.0 mm, and GFS predicts 103.0 mm.",
      concept: "No single NWP or AI model is universally superior. Each has regime-dependent strengths and biases."
    },
    {
      step: 2,
      title: "Step 2: Quantifying Epistemic Disagreement",
      subtitle: "Separating Confidence from Event Probability",
      description: "Instead of averaging divergent numbers, VARUNA computes weighted spread (±23.8 mm) and variance (566.4). Even though the probability of heavy rain is high (78.4%), VARUNA flags inter-model disagreement as HIGH and calibrates operational confidence to MEDIUM.",
      concept: "High probability does NOT equal high confidence when physical and neural models disagree."
    },
    {
      step: 3,
      title: "Step 3: Context-Dependent Trust Assignment",
      subtitle: "Evaluating Historical Skill, Lead Time, & Regime",
      description: "VARUNA's trust engine queries historical verification databases for Telangana during Southwest Monsoon conditions at a 48h lead horizon. NCUM has the lowest error variance and zero recent bias, while GFS has a recognized wet-bias penalty.",
      concept: "Trust is conditioned on spatial orography, weather regime, and forecast lead time."
    },
    {
      step: 4,
      title: "Step 4: Simplex Adaptive Weight Vector",
      subtitle: "Satisfying Mathematical Rigor (Σw_i = 1.0)",
      description: "Using a Supervised ML Meta-Model (GBDT + Softmax), weights are assigned: NCUM = 46%, WRF = 31%, AI Weather = 18%, GFS = 5%. The sum strictly equals 1.0.",
      concept: "Adaptive weights prevent arbitrary ad-hoc adjustments and ensure scientific validity."
    },
    {
      step: 5,
      title: "Step 5: The Fused Forecast Layer",
      subtitle: "Explainable Blending Output",
      description: "The resulting fused rainfall is 70.1 mm. Notice that this is NOT a simple average (74.0 mm) or static blend (71.9 mm). It actively damps the wet GFS outlier while preserving NCUM's synoptic skill and WRF's convective structure.",
      concept: "VARUNA is evaluated on a leak-free chronological benchmark against simple averaging, a static blend and each raw model; see the Verification Centre for the measured MAE change."
    },
    {
      step: 6,
      title: "Step 6: Real-Time Resilience & Model Dropout",
      subtitle: "What Happens When a Source Fails?",
      description: "Imagine WRF 3km communication fails or is delayed. Click below to inject a simulated WRF dropout.",
      concept: "In critical defense & disaster management, the system must never crash on feed failure.",
      actionText: "Inject WRF Dropout",
      action: () => setSimulatedDisabledModel('WRF')
    },
    {
      step: 7,
      title: "Step 7: Autonomous Weight Rebalancing",
      subtitle: "Simplex Preservation Under Missing Inputs",
      description: "Notice how VARUNA gracefully responded: WRF weight dropped to 0%, while NCUM rose to 63%, AI Weather to 25%, and GFS to 12%. The fused forecast recalculated to 72.8 mm with zero operator downtime.",
      concept: "Graceful degradation without human intervention."
    },
    {
      step: 8,
      title: "Step 8: Verification Loop",
      subtitle: "Continuous Ground Truth Comparison",
      description: "As actual rainfall observations arrive (IMDAA reanalysis / AWS stations), VARUNA computes MAE and RMSE against fused output vs all individual models. Fused MAE remains lower than all individual models.",
      concept: "A forecast system without continuous verification is open-loop speculation."
    },
    {
      step: 9,
      title: "Step 9: Exponential Moving Average (EMA) Learning",
      subtitle: "Updating Model Reliability Memory",
      description: "Recent errors update each model's reliability memory via EMA (λ = 0.95). If WRF continues to over-dampen convective rainfall, its future weight in that regime is automatically decayed.",
      concept: "VERIFY → LEARN → TRUST"
    },
    {
      step: 10,
      title: "Step 10: Complete Decision-Support Intelligence",
      subtitle: "Mission Control Ready for MoES / NCMRWF",
      description: "You have witnessed the complete VARUNA operational loop: Multi-model Ingestion → Disagreement Quantification → Contextual Trust → Adaptive Fusion → XAI Explanation → Continuous Verification → Failure Memory.",
      concept: "VARUNA: Turning heterogeneous models into verified, explainable forecast intelligence."
    }
  ];

  const currentStep = steps[currentStepIndex];

  const handleNext = () => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    } else {
      setIsDemoModalOpen(false);
      setActiveRoute('control-room');
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const handleClose = () => {
    setIsDemoModalOpen(false);
    setSimulatedDisabledModel(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-fadeIn">
      <div className="w-full max-w-2xl bg-surface-container-lowest border border-outline-variant/30 rounded-2xl shadow-2xl p-6 sm:p-8 flex flex-col justify-between min-h-[500px]">
        {/* Header */}
        <div>
          <div className="flex items-center justify-between pb-4 border-b border-outline-variant/30">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-on-primary font-bold shadow-xs">
                <Play className="w-4 h-4 fill-white text-white" />
              </div>
              <div>
                <h3 className="font-headline font-bold text-lg text-on-surface flex items-center gap-2">
                  <span>VARUNA GUIDED DEMO</span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-primary-container text-on-primary-container font-bold">
                    STEP {currentStep.step} / 10
                  </span>
                </h3>
                <span className="text-xs font-mono text-on-surface-variant">
                  SIH26081 · MoES / NCMRWF · Guided product walkthrough
                </span>
              </div>
            </div>
            <button
              onClick={handleClose}
              className="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="my-4">
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="GUIDED DEMONSTRATION WORKFLOW" />
          </div>

          {/* Step Body */}
          <div className="space-y-4 my-6">
            <div>
              <div className="text-xs font-mono text-primary uppercase tracking-widest font-bold">
                {currentStep.subtitle}
              </div>
              <h4 className="font-headline font-extrabold text-xl text-on-surface mt-1">
                {currentStep.title}
              </h4>
            </div>

            <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/30 text-sm text-on-surface leading-relaxed font-body">
              {currentStep.description}
            </div>

            {currentStep.action && (
              <div className="flex justify-start">
                <button
                  onClick={currentStep.action}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-headline font-bold text-xs uppercase tracking-wide flex items-center gap-2 transition-all shadow-md"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{currentStep.actionText}</span>
                </button>
              </div>
            )}

            <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/30 text-xs font-mono text-on-surface flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <strong className="text-primary font-bold">Core Scientific Insight:</strong> {currentStep.concept}
              </div>
            </div>
          </div>
        </div>

        {/* Footer controls */}
        <div className="pt-4 border-t border-outline-variant/30 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {steps.map((s, idx) => (
              <button
                key={s.step}
                onClick={() => setCurrentStepIndex(idx)}
                className={`w-2.5 h-2.5 rounded-full transition-all ${
                  idx === currentStepIndex
                    ? 'w-7 bg-primary'
                    : idx < currentStepIndex
                    ? 'bg-outline-variant'
                    : 'bg-outline-variant/40'
                }`}
                title={`Jump to Step ${s.step}`}
              />
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handlePrev}
              disabled={currentStepIndex === 0}
              className="px-3 py-2 rounded-lg bg-surface-container-low hover:bg-surface-container-high disabled:opacity-40 text-on-surface font-mono text-xs border border-outline-variant/30 flex items-center gap-1 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>
            <button
              onClick={handleNext}
              className="px-5 py-2 rounded-lg bg-primary hover:bg-primary/90 text-on-primary font-headline font-bold text-xs uppercase tracking-wide flex items-center gap-1.5 transition-all shadow-xs"
            >
              <span>{currentStepIndex === steps.length - 1 ? 'Finish & Enter Control Room' : 'Next Step'}</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
