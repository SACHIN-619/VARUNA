import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useScroll, useTransform, useSpring } from 'framer-motion';
import { 
  ShieldCheck, 
  Sparkles, 
  Layers, 
  Cpu, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  TrendingUp, 
  ArrowRight, 
  ChevronDown, 
  Database, 
  Eye, 
  RefreshCw, 
  Compass, 
  Play, 
  UserCheck, 
  Terminal, 
  BarChart3, 
  Zap, 
  Globe, 
  Lock, 
  FileText,
  HelpCircle,
  Sliders,
  GitMerge
} from 'lucide-react';

interface LandingPageProps {
  onEnterApp: () => void;
  onOpenLogin: () => void;
  onSelectRole?: (role: string) => void;
  /** When a session exists the nav shows Dashboard + Sign out instead of Sign in. */
  loggedIn?: boolean;
  userLabel?: string;
  onSignOut?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterApp, onOpenLogin, onSelectRole, loggedIn = false, userLabel, onSignOut }) => {
  const [activeStage, setActiveStage] = useState<number>(1);
  const [scrolled, setScrolled] = useState<boolean>(false);
  const [storyFrame, setStoryFrame] = useState<number>(1);
  
  // Interactive Simulator State (Demo Values)
  const [simRegion, setSimRegion] = useState<string>('TELANGANA');
  const [simLead, setSimLead] = useState<number>(48);
  const [simRegime, setSimRegime] = useState<string>('HEAVY_RAINFALL');

  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef });
  const springProgress = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Simulator Weights Calculation (Demo Illustrative Values)
  const getSimWeights = () => {
    if (simRegion === 'TELANGANA' && simRegime === 'HEAVY_RAINFALL') {
      return { NCUM: 46, WRF: 31, AI_WEATHER: 18, GFS: 5, fused: 70.1, disagreement: 'HIGH' };
    } else if (simRegion === 'WESTERN_GHATS') {
      return { NCUM: 32, WRF: 48, AI_WEATHER: 15, GFS: 5, fused: 142.5, disagreement: 'MEDIUM' };
    } else if (simRegion === 'ODISHA') {
      return { NCUM: 22, WRF: 28, AI_WEATHER: 42, GFS: 8, fused: 88.4, disagreement: 'HIGH' };
    } else {
      return { NCUM: 40, WRF: 30, AI_WEATHER: 20, GFS: 10, fused: 45.2, disagreement: 'LOW' };
    }
  };

  const simWeights = getSimWeights();

  const pipelineStages = [
    { num: "01", title: "Ingest", desc: "Streams heterogeneous NWP (NCUM 12km, WRF 3km, GFS 25km) & AI forecast feeds with SHA-256 audit hashes.", icon: Database },
    { num: "02", title: "Quality Control", desc: "Validates physical meteorological boundaries [0, 500mm], flagging invalid negatives & sensor spikes.", icon: ShieldCheck },
    { num: "03", title: "Harmonization", desc: "Normalizes units (mm/day -> mm, K -> °C) and regrids grid bounds to target centroids.", icon: Layers },
    { num: "04", title: "Context Engine", desc: "Classifies atmospheric synoptic conditions, monsoon regime, season, and forecast lead time.", icon: Compass },
    { num: "05", title: "Historical Skill", desc: "Queries regional ModelSkill memory records evaluating historical MAE across sub-divisions.", icon: BarChart3 },
    { num: "06", title: "Adaptive ML Trust", desc: "Gradient Boosting Meta-Model calculates convex weights (sum w_i = 1) conditioned on context.", icon: Cpu },
    { num: "07", title: "Model Disagreement", desc: "Quantifies multi-model spread, std dev, and variance across ensemble predictions.", icon: Activity },
    { num: "08", title: "Forecast Fusion", desc: "Synthesizes optimal convex combination sum(w_i * F_i) alongside static & simple baselines.", icon: Zap },
    { num: "09", title: "Uncertainty Engine", desc: "Constructs P10/P50/P90 confidence envelopes and CRPS score indicators.", icon: TrendingUp },
    { num: "10", title: "Extreme Signal", desc: "Evaluates operational IMD threat thresholds (>= 64.5mm Heavy, >= 115.5mm Extreme).", icon: AlertTriangle },
    { num: "11", title: "Provenance & XAI", desc: "Generates SHAP feature drivers and human-readable operational briefings.", icon: Sparkles },
    { num: "12", title: "Intelligence Package", desc: "Assembles unified ForecastIntelligencePackage JSON payload consumed by UI & API.", icon: FileText },
    { num: "13", title: "Observation Verify", desc: "Pairs forecast with post-event ground-truth observations (AWS & Doppler radar).", icon: CheckCircle2 },
    { num: "14", title: "Skill-Memory Feedback", desc: "Updates ModelSkill database rows via Exponential Moving Average (EMA) for next cycle.", icon: RefreshCw }
  ];

  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  return (
    <div ref={containerRef} className="min-h-screen bg-[#070c18] text-[#e2e8f8] font-sans antialiased selection:bg-cyan-400 selection:text-slate-950 overflow-x-hidden">
      
      {/* 1. FLOATING GLASS NAVIGATION BAR */}
      <header className={`fixed top-4 left-1/2 -translate-x-1/2 w-[94%] max-w-7xl z-50 transition-all duration-300 ${
        scrolled ? 'bg-[#0d172e]/95 backdrop-blur-xl border border-cyan-400/40 shadow-2xl shadow-cyan-950/60 rounded-full px-6 py-3.5' : 'bg-transparent rounded-full px-6 py-4'
      }`}>
        <div className="flex items-center justify-between">
          {/* Brand Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <img src="/assets/varuna/VARUNA_LOGO.png" alt="VARUNA Logo" className="h-8 w-auto object-contain drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]" />
            <div className="flex flex-col">
              <span className="font-headline font-extrabold text-lg tracking-tight text-white flex items-center gap-2">
                VARUNA
                <span className="text-[10px] font-mono font-bold bg-cyan-500/30 text-cyan-200 border border-cyan-400/60 px-2 py-0.5 rounded uppercase shadow-sm">
                  SIH26081
                </span>
              </span>
              <span className="text-[10px] font-mono text-cyan-200 font-semibold">Adaptive Forecast Intelligence</span>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden 2xl:flex items-center gap-5 font-mono text-[11px] uppercase tracking-wider text-white font-bold whitespace-nowrap">
            <a href="#hero" className="hover:text-cyan-300 transition-colors drop-shadow-sm">Overview</a>
            <a href="#challenge" className="hover:text-cyan-300 transition-colors drop-shadow-sm">The Challenge</a>
            <a href="#story-sequence" className="hover:text-cyan-300 transition-colors drop-shadow-sm">Problem to Answer</a>
            <a href="#fits" className="hover:text-cyan-300 transition-colors drop-shadow-sm">Where VARUNA Fits</a>
            <a href="#pipeline" className="hover:text-cyan-300 transition-colors drop-shadow-sm">Pipeline</a>
            <a href="#trust" className="hover:text-cyan-300 transition-colors drop-shadow-sm">Trust Engine</a>
            <a href="#verification" className="hover:text-cyan-300 transition-colors drop-shadow-sm">Verification</a>
          </nav>

          {/* Right Action CTAs */}
          <div className="flex items-center gap-2 shrink-0">
            {loggedIn ? (
              <>
                {userLabel && <span className="hidden 2xl:inline font-mono text-[11px] text-cyan-100 max-w-[180px] truncate">{userLabel}</span>}
                <button
                  onClick={onEnterApp}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:from-cyan-300 hover:to-teal-200 rounded-full shadow-lg shadow-cyan-500/30 transition-colors"
                >
                  <Zap className="w-3.5 h-3.5 fill-slate-950" />
                  Dashboard
                </button>
                <button
                  onClick={onSignOut}
                  className="px-4 py-2 text-xs font-mono font-bold text-white hover:text-rose-200 bg-slate-800/90 hover:bg-slate-700 border border-rose-400/50 rounded-full transition-colors"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={onOpenLogin}
                  className="px-4 py-2 text-xs font-mono font-bold text-white hover:text-cyan-300 bg-slate-800/90 hover:bg-slate-700 border border-cyan-500/40 rounded-full transition-colors"
                >
                  Sign in
                </button>
                <button
                  onClick={onOpenLogin}
                  className="hidden sm:flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:from-cyan-300 hover:to-teal-200 rounded-full shadow-lg shadow-cyan-500/30 transition-colors"
                >
                  <Zap className="w-3.5 h-3.5 fill-slate-950" />
                  Enter VARUNA
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* 2. HERO SECTION WITH BACKGROUND VIDEO */}
      <section id="hero" className="relative min-h-screen flex items-center justify-center pt-36 md:pt-40 pb-16 px-4 overflow-hidden">
        {/* Hero Background Video Asset */}
        <div className="absolute inset-0 z-0 overflow-hidden">
          <video
            autoPlay
            loop
            muted
            playsInline
            poster="/assets/varuna/screen.png"
            className="w-full h-full object-cover opacity-35 scale-105 filter saturate-150 contrast-125"
          >
            <source src="/assets/varuna/Hero_background_video.mp4" type="video/mp4" />
          </video>
          <div className="absolute inset-0 bg-gradient-to-b from-[#070c18]/60 via-[#070c18]/80 to-[#070c18]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-500/15 via-transparent to-transparent pointer-events-none" />
          <div className="absolute inset-0 bg-met-grid opacity-30 pointer-events-none" />
        </div>

        {/* Floating Particle Models Animation */}
        <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden">
          <motion.div 
            animate={{ y: [0, -15, 0], opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
            className="absolute top-1/4 left-[12%] font-mono text-xs bg-slate-900/90 border border-cyan-400/60 text-cyan-200 px-3.5 py-2 rounded-lg shadow-2xl font-bold"
          >
            NCUM 12km • 82.0mm
          </motion.div>

          <motion.div 
            animate={{ y: [0, 15, 0], opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 1 }}
            className="absolute top-1/3 right-[12%] font-mono text-xs bg-slate-900/90 border border-indigo-400/60 text-indigo-200 px-3.5 py-2 rounded-lg shadow-2xl font-bold"
          >
            GFS 25km • 103.0mm
          </motion.div>

          <motion.div 
            animate={{ y: [0, -20, 0], opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut", delay: 2 }}
            className="absolute bottom-1/3 left-[15%] font-mono text-xs bg-slate-900/90 border border-teal-400/60 text-teal-200 px-3.5 py-2 rounded-lg shadow-2xl font-bold"
          >
            WRF 3km • 47.0mm
          </motion.div>

          <motion.div 
            animate={{ y: [0, 20, 0], opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 6.5, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
            className="absolute bottom-1/4 right-[16%] font-mono text-xs bg-slate-900/90 border border-purple-400/60 text-purple-200 px-3.5 py-2 rounded-lg shadow-2xl font-bold"
          >
            AI WEATHER • 64.0mm
          </motion.div>
        </div>

        {/* Hero Content Stack */}
        <div className="relative z-20 max-w-5xl mx-auto text-center flex flex-col items-center gap-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-950/80 border border-cyan-400/60 text-cyan-200 text-xs font-mono font-bold uppercase tracking-widest shadow-lg"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Adaptive Multi-Model NWP & AI Forecast Intelligence
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.2 }}
            className="font-headline font-extrabold text-4xl sm:text-6xl md:text-7xl tracking-tight text-white leading-[1.1] drop-shadow-lg"
          >
            WEATHER MODELS <br className="hidden sm:inline"/>
            <span className="bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-300 bg-clip-text text-transparent">
              SEE DIFFERENTLY.
            </span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.4 }}
            className="font-headline text-xl sm:text-2xl text-white font-extrabold tracking-wide max-w-3xl drop-shadow-md"
          >
            VARUNA DECIDES HOW MUCH TO TRUST EACH ONE.
          </motion.p>

          <motion.blockquote 
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.5 }}
            className="text-base sm:text-lg italic text-cyan-100 max-w-2xl border-l-4 border-cyan-400 pl-4 text-left my-2 font-serif font-medium bg-slate-950/40 py-2 pr-2 rounded-r-lg"
          >
            “Don’t ask which weather model is the best. Ask which model should be trusted, where, when, and by how much.”
          </motion.blockquote>

          <motion.p 
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.55 }}
            className="text-xs sm:text-sm text-slate-100 max-w-2xl leading-relaxed font-mono font-medium drop-shadow"
          >
            VARUNA is not another weather model. It is an adaptive intelligence layer for evaluating conditional reliability, blending heterogeneous signals, and exposing operational disagreement across existing forecasting systems.
          </motion.p>

          {/* Hero CTAs */}
          <motion.div 
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.6 }}
            className="flex flex-wrap items-center justify-center gap-4 pt-4"
          >
            <a
              href="#challenge"
              className="px-7 py-3.5 text-xs font-mono font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-full transition-all shadow-xl shadow-cyan-500/30 flex items-center gap-2 group"
            >
              Explore The Problem Narrative
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>

            <button
              onClick={onOpenLogin}
              className="px-7 py-3.5 text-xs font-mono font-bold text-white hover:text-cyan-300 bg-slate-900 hover:bg-slate-800 border-2 border-cyan-400/80 rounded-full transition-all flex items-center gap-2 shadow-xl shadow-cyan-950/60"
            >
              <Zap className="w-4 h-4 text-cyan-400" />
              Enter Forecast Intelligence
            </button>
          </motion.div>

          <motion.a
            href="#challenge"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.9 }}
            transition={{ delay: 1, duration: 1 }}
            className="text-xs font-mono font-bold text-cyan-300 hover:text-white flex items-center gap-1 mt-6 transition-colors"
          >
            Understand The Challenge ↓
          </motion.a>
        </div>
      </section>

      {/* 3. 02 — THE CURRENT CHALLENGE */}
      <section id="challenge" className="py-28 px-4 bg-slate-950/95 border-t border-slate-900 relative overflow-hidden">
        {/* Visual Map Background Layer */}
        <div className="absolute inset-0 opacity-20 pointer-events-none mix-blend-screen">
          <img 
            src="/assets/varuna/varuna_problem_visual.jpg" 
            alt="VARUNA Problem Visualization" 
            className="w-full h-full object-cover filter saturate-150 contrast-125"
          />
        </div>

        <div className="max-w-7xl mx-auto space-y-16 relative z-10">
          {/* Section Header */}
          <div className="text-center space-y-4 max-w-4xl mx-auto">
            <span className="text-xs font-mono uppercase tracking-widest text-amber-300 font-bold border border-amber-400/60 bg-amber-950/80 px-3 py-1 rounded-full shadow-md">
              Core Problem & Gap Statement
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white tracking-tight drop-shadow-md">
              THE PROBLEM ISN’T A LACK OF FORECASTS.
            </h2>
            <p className="font-headline text-lg sm:text-2xl text-cyan-300 font-bold tracking-wide">
              WEATHER MODELS ALREADY SEE THE STORM. <br />
              <span className="text-slate-100">THE HARDER QUESTION IS: WHICH SIGNAL SHOULD WE TRUST?</span>
            </p>
            <p className="text-sm font-mono text-slate-200 max-w-3xl mx-auto leading-relaxed font-medium">
              Modern forecasting produces multiple valuable signals. The challenge is interpreting their conditional reliability across changing geography, lead time, season, and synoptic weather regimes.
            </p>
          </div>

          {/* 3-Column Problem -> Context -> Solution Flow */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
            
            {/* Left Column: Scattered Forecast Signals */}
            <div className="lg:col-span-4 bg-[#0d162a] border border-slate-700/80 rounded-2xl p-6 space-y-6 flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex items-center justify-between border-b border-slate-700/80 pb-3 mb-4">
                  <span className="text-xs font-mono font-bold text-white uppercase flex items-center gap-2">
                    <Database className="w-4 h-4 text-cyan-400" />
                    Multiple NWP & AI Feeds
                  </span>
                  <span className="text-[10px] font-mono font-bold text-amber-300 bg-amber-950/80 border border-amber-400/60 px-2.5 py-0.5 rounded">
                    ILLUSTRATIVE SCENARIO
                  </span>
                </div>

                <div className="space-y-3">
                  {[
                    { id: 'NCUM', val: '82.0 mm', bg: 'border-cyan-400/60 text-cyan-300', tag: 'NCMRWF Global NWP' },
                    { id: 'GFS', val: '103.0 mm', bg: 'border-indigo-400/60 text-indigo-300', tag: 'NOAA GFS 25km' },
                    { id: 'WRF', val: '47.0 mm', bg: 'border-teal-400/60 text-teal-300', tag: 'Regional High-Res' },
                    { id: 'AI_WEATHER', val: '64.0 mm', bg: 'border-purple-400/60 text-purple-300', tag: 'Neural Operator AI' },
                  ].map((m) => (
                    <div key={m.id} className={`bg-slate-950 border ${m.bg} rounded-xl p-3.5 flex items-center justify-between shadow-md`}>
                      <div>
                        <div className="font-mono font-extrabold text-xs text-white">{m.id}</div>
                        <div className="text-[10px] font-mono text-slate-300 font-semibold">{m.tag}</div>
                      </div>
                      <div className={`font-mono font-extrabold text-xl ${m.bg.split(' ')[1]}`}>
                        {m.val}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-amber-950/60 border border-amber-400/60 rounded-xl p-4 text-xs font-mono text-amber-100 font-medium">
                <span className="font-bold text-amber-300">Divergent Signals:</span> Spread of 56.0 mm precipitation creates massive decision risk for operational forecasters.
              </div>
            </div>

            {/* Middle Column: The Context Multiplier */}
            <div className="lg:col-span-4 bg-[#0e1b38] border-2 border-cyan-400/60 rounded-2xl p-6 space-y-6 flex flex-col justify-between shadow-2xl shadow-cyan-950/50 relative">
              <div className="absolute -top-3 left-6 text-[10px] font-mono font-extrabold bg-amber-400 text-slate-950 px-3 py-0.5 rounded uppercase shadow-md">
                The Fundamental Gap
              </div>

              <div>
                <h3 className="font-headline font-extrabold text-lg text-white mb-2 flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-amber-400" />
                  MODEL RELIABILITY IS CONDITIONAL.
                </h3>
                <p className="text-xs text-slate-100 leading-relaxed font-mono font-medium mb-4">
                  A model that performs well in one region, lead time or weather regime may not be the strongest signal in another.
                </p>

                <div className="grid grid-cols-2 gap-2 text-center">
                  {[
                    "REGION",
                    "LEAD TIME",
                    "SEASON",
                    "WEATHER REGIME",
                    "RECENT SKILL",
                    "DISAGREEMENT"
                  ].map((ctx) => (
                    <div key={ctx} className="bg-slate-950 border border-cyan-500/40 rounded-lg p-2.5 font-mono text-xs font-extrabold text-cyan-300 shadow-sm">
                      {ctx}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-[#0c1a36] border-2 border-cyan-400 rounded-xl p-5 text-xs font-mono text-white leading-relaxed shadow-xl">
                <span className="font-extrabold text-cyan-300">The Decision Dilemma:</span> Without continuous skill evaluation, static ensemble averaging degrades forecast precision during extreme events.
              </div>
            </div>

            {/* Right Column: VARUNA Intelligence Layer */}
            <div className="lg:col-span-4 bg-gradient-to-b from-cyan-950/60 via-slate-900 to-slate-950 border-2 border-cyan-400/80 rounded-2xl p-6 space-y-6 flex flex-col justify-between shadow-2xl">
              <div>
                <div className="flex items-center gap-2 text-xs font-mono font-extrabold text-cyan-300 uppercase mb-3">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  VARUNA Intelligence & Fusion Layer
                </div>

                <div className="bg-slate-950 border border-cyan-400/60 rounded-xl p-4 space-y-3 shadow-inner">
                  <div className="grid grid-cols-3 gap-1 text-center font-mono text-[10px] text-cyan-200 font-bold">
                    <div className="bg-slate-900 p-2 rounded border border-cyan-500/30">TRUST</div>
                    <div className="bg-slate-900 p-2 rounded border border-cyan-500/30">SPREAD</div>
                    <div className="bg-slate-900 p-2 rounded border border-cyan-500/30">CONTEXT</div>
                  </div>

                  <div className="text-center font-mono text-xs text-cyan-300 font-bold py-1">
                    ↓ Gradient Boosting ML Blending ↓
                  </div>

                  <div className="bg-[#0a1e3f] border-2 border-cyan-400 rounded-xl p-4 text-center shadow-xl">
                    <div className="text-xs font-mono text-cyan-200 font-bold uppercase">ADAPTIVE FUSED FORECAST</div>
                    <div className="text-3xl font-mono font-black text-white drop-shadow-md">70.1 mm</div>
                    <div className="text-xs font-mono text-emerald-300 font-bold mt-1">P10: 58.2mm • P90: 84.5mm</div>
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-800 pt-4 text-center">
                <h4 className="font-headline font-extrabold text-sm text-white tracking-tight">
                  VARUNA DOESN’T REPLACE THE MODELS.
                </h4>
                <p className="text-xs font-mono text-cyan-300 font-extrabold mt-1">
                  IT INTELLIGENTLY INTERPRETS THEIR SIGNALS.
                </p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* 4. 03 — PROBLEM TO ANSWER SCROLL STORY SEQUENCE */}
      <section id="story-sequence" className="py-24 px-4 bg-[#050914] border-t border-slate-900 relative">
        <div className="max-w-5xl mx-auto space-y-12">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold">
              Step-by-Step Narrative Sequence
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-4xl text-white drop-shadow">
              FROM MULTIPLE FORECASTS TO FORECAST INTELLIGENCE
            </h2>
            <p className="text-sm font-mono text-slate-200 max-w-xl mx-auto font-medium">
              Click through the frames below to see how VARUNA transforms fragmented model outputs into trusted decision intelligence.
            </p>
          </div>

          {/* Interactive Frame Selector Tabs */}
          <div className="flex flex-wrap items-center justify-center gap-3">
            {[
              { id: 1, label: "01. Different Signals" },
              { id: 2, label: "02. Which is Right?" },
              { id: 3, label: "03. It Depends" },
              { id: 4, label: "04. VARUNA Processing" },
              { id: 5, label: "05. Forecast Intelligence" }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setStoryFrame(tab.id)}
                className={`px-5 py-2.5 text-xs font-mono font-extrabold rounded-full transition-all border-2 shadow-lg ${
                  storyFrame === tab.id
                    ? 'bg-cyan-400 text-slate-950 border-cyan-300 shadow-cyan-500/50 scale-105'
                    : 'bg-[#0d1c3a] text-white border-cyan-500/50 hover:bg-[#132854] hover:text-cyan-200 hover:border-cyan-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Frame Display Canvas */}
          <div className="bg-slate-900/95 border-2 border-cyan-400/60 rounded-2xl p-8 sm:p-12 min-h-[380px] flex items-center justify-center relative overflow-hidden shadow-2xl">
            <AnimatePresence mode="wait">
              {storyFrame === 1 && (
                <motion.div
                  key="frame1"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.05 }}
                  className="w-full text-center space-y-6"
                >
                  <div className="inline-flex items-center gap-2 text-xs font-mono text-white font-bold uppercase bg-slate-950 px-3.5 py-1.5 rounded-full border border-slate-700">
                    Frame 1: Raw NWP Output Disagreement
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto">
                    <div className="bg-slate-950 p-4 rounded-xl border-2 border-cyan-400/60 shadow-md">
                      <div className="font-mono text-xs text-cyan-300 font-bold">NCUM</div>
                      <div className="text-2xl font-mono font-black text-white mt-1">82 mm</div>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-xl border-2 border-indigo-400/60 shadow-md">
                      <div className="font-mono text-xs text-indigo-300 font-bold">GFS</div>
                      <div className="text-2xl font-mono font-black text-white mt-1">103 mm</div>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-xl border-2 border-teal-400/60 shadow-md">
                      <div className="font-mono text-xs text-teal-300 font-bold">WRF</div>
                      <div className="text-2xl font-mono font-black text-white mt-1">47 mm</div>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-xl border-2 border-purple-400/60 shadow-md">
                      <div className="font-mono text-xs text-purple-300 font-bold">AI WEATHER</div>
                      <div className="text-2xl font-mono font-black text-white mt-1">64 mm</div>
                    </div>
                  </div>
                  <p className="font-headline text-2xl text-white font-extrabold tracking-wide drop-shadow-md">
                    Four capable models. Four divergent rainfall predictions.
                  </p>
                </motion.div>
              )}

              {storyFrame === 2 && (
                <motion.div
                  key="frame2"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.05 }}
                  className="w-full text-center space-y-6"
                >
                  <div className="inline-flex items-center gap-2 text-xs font-mono text-amber-300 font-bold uppercase bg-amber-950/60 px-3.5 py-1.5 rounded-full border border-amber-400/60">
                    <HelpCircle className="w-4 h-4" /> Frame 2: The Core Question
                  </div>
                  <h3 className="font-headline font-extrabold text-4xl sm:text-5xl text-white drop-shadow">
                    WHICH ONE IS RIGHT?
                  </h3>
                  <p className="text-sm font-mono text-slate-100 max-w-xl mx-auto font-medium">
                    Picking one model arbitrarily or relying on fixed rules risks missing extreme weather hazards.
                  </p>
                </motion.div>
              )}

              {storyFrame === 3 && (
                <motion.div
                  key="frame3"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.05 }}
                  className="w-full text-center space-y-6"
                >
                  <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-200 font-bold uppercase bg-cyan-950/60 px-3.5 py-1.5 rounded-full border border-cyan-400/60">
                    Frame 3: The Reality
                  </div>
                  <h3 className="font-headline font-extrabold text-4xl sm:text-5xl text-cyan-300 drop-shadow">
                    IT DEPENDS.
                  </h3>
                  <p className="text-xs font-mono text-slate-100 max-w-md mx-auto font-bold">
                    Model reliability changes dynamically across:
                  </p>
                  <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl mx-auto font-mono text-xs text-white font-extrabold">
                    <span className="bg-slate-950 px-3.5 py-2 rounded border border-cyan-400/60">REGION</span>
                    <span className="bg-slate-950 px-3.5 py-2 rounded border border-cyan-400/60">LEAD TIME</span>
                    <span className="bg-slate-950 px-3.5 py-2 rounded border border-cyan-400/60">SEASON</span>
                    <span className="bg-slate-950 px-3.5 py-2 rounded border border-cyan-400/60">WEATHER REGIME</span>
                    <span className="bg-slate-950 px-3.5 py-2 rounded border border-cyan-400/60">RECENT SKILL</span>
                    <span className="bg-slate-950 px-3.5 py-2 rounded border border-cyan-400/60">DISAGREEMENT</span>
                  </div>
                </motion.div>
              )}

              {storyFrame === 4 && (
                <motion.div
                  key="frame4"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.05 }}
                  className="w-full text-center space-y-6"
                >
                  <div className="inline-flex items-center gap-2 text-xs font-mono text-teal-200 font-bold uppercase bg-teal-950/60 px-3.5 py-1.5 rounded-full border border-teal-400/60">
                    Frame 4: Processing
                  </div>
                  <div className="font-headline font-extrabold text-3xl text-white drop-shadow">
                    EVERYTHING FLOWS INTO VARUNA
                  </div>
                  <div className="flex items-center justify-center gap-2 font-mono text-xs text-cyan-200 font-extrabold flex-wrap">
                    <span className="bg-slate-950 px-3 py-1.5 rounded border border-cyan-400/60">CONTEXT</span>
                    <span>→</span>
                    <span className="bg-slate-950 px-3 py-1.5 rounded border border-cyan-400/60">TRUST WEIGHTS</span>
                    <span>→</span>
                    <span className="bg-slate-950 px-3 py-1.5 rounded border border-cyan-400/60">FUSION</span>
                    <span>→</span>
                    <span className="bg-slate-950 px-3 py-1.5 rounded border border-cyan-400/60">UNCERTAINTY</span>
                    <span>→</span>
                    <span className="bg-slate-950 px-3 py-1.5 rounded border border-cyan-400/60">VERIFICATION</span>
                  </div>
                </motion.div>
              )}

              {storyFrame === 5 && (
                <motion.div
                  key="frame5"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.05 }}
                  className="w-full text-center space-y-6"
                >
                  <div className="inline-flex items-center gap-2 text-xs font-mono text-emerald-200 font-bold uppercase bg-emerald-950/60 px-3.5 py-1.5 rounded-full border border-emerald-400/60">
                    Frame 5: The Outcome
                  </div>
                  <h3 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow-lg">
                    FROM MULTIPLE FORECASTS TO FORECAST INTELLIGENCE.
                  </h3>
                  <div className="pt-2">
                    <button
                      onClick={onOpenLogin}
                      className="px-8 py-3.5 text-xs font-mono font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-full transition-all shadow-xl shadow-cyan-500/30"
                    >
                      Enter Operational Intelligence Center
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </section>

      {/* 5. 04 — WHERE VARUNA FITS VISUAL DIAGRAM */}
      <section id="fits" className="py-24 px-4 bg-[#070c18] border-t border-slate-900 relative">
        <div className="max-w-6xl mx-auto space-y-16">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold border border-cyan-400/60 px-3 py-1 rounded-full bg-cyan-950/60">
              System Architecture & Integration
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow">
              WHERE VARUNA FITS
            </h2>
            <p className="text-sm font-mono text-slate-100 max-w-2xl mx-auto leading-relaxed font-medium">
              VARUNA is not another weather model. It is an adaptive intelligence layer for understanding, weighting, and combining existing forecast signals.
            </p>
          </div>

          {/* 3-Tier Visual Box Architecture */}
          <div className="max-w-3xl mx-auto space-y-4">
            
            {/* Box 1: Existing Ecosystem */}
            <div className="bg-[#0e1933] border border-slate-700/80 rounded-2xl p-6 text-center space-y-3 shadow-lg">
              <div className="text-xs font-mono font-extrabold text-slate-200 uppercase tracking-widest">
                EXISTING FORECAST ECOSYSTEM
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3 font-mono text-xs text-white font-bold">
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-slate-700">NCUM (MoES/NCMRWF)</span>
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-slate-700">GFS (NOAA)</span>
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-slate-700">WRF (High-Res)</span>
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-slate-700">AI WEATHER MODELS</span>
              </div>
              <div className="text-xs font-mono text-slate-300 font-medium">
                + Ground Observations / Reference Radar Data
              </div>
            </div>

            {/* Down Arrow 1 */}
            <div className="flex justify-center text-cyan-400">
              <ChevronDown className="w-8 h-8" />
            </div>

            {/* Box 2: VARUNA Intelligence Layer */}
            <div className="bg-[#091f42] border-2 border-cyan-400 rounded-2xl p-6 text-center space-y-3 shadow-2xl shadow-cyan-950/60 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-mono font-extrabold bg-cyan-400 text-slate-950 px-3 py-0.5 rounded-full uppercase shadow-md">
                INTELLIGENCE LAYER
              </div>
              <div className="font-headline font-extrabold text-2xl text-white tracking-wide">
                VARUNA
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs text-cyan-200 font-bold">
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">Context Engine</div>
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">Historical Skill</div>
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">ML Trust Weights</div>
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">Disagreement Spread</div>
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">Adaptive Fusion</div>
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">Uncertainty Envelopes</div>
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">SHAP Explanations</div>
                <div className="bg-slate-950 p-2 rounded border border-cyan-500/40">Skill Verification</div>
              </div>
            </div>

            {/* Down Arrow 2 */}
            <div className="flex justify-center text-cyan-400">
              <ChevronDown className="w-8 h-8" />
            </div>

            {/* Box 3: Forecast Intelligence Output */}
            <div className="bg-gradient-to-r from-slate-900 via-[#0e1933] to-cyan-950 border border-slate-700 rounded-2xl p-6 text-center space-y-3 shadow-xl">
              <div className="text-xs font-mono font-extrabold text-emerald-300 uppercase tracking-widest">
                DECISION-READY FORECAST INTELLIGENCE
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3 font-mono text-xs font-bold">
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-emerald-400/60 text-emerald-300">Fused Forecast</span>
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-cyan-400/60 text-cyan-300">Dynamic Model Trust</span>
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-indigo-400/60 text-indigo-300">P10/P50/P90 Uncertainty</span>
                <span className="bg-slate-950 px-3 py-1.5 rounded border border-amber-400/60 text-amber-300">IMD Extreme Signals</span>
              </div>
            </div>

          </div>

          <div className="text-center font-mono text-xs text-slate-200 font-bold max-w-xl mx-auto pt-4">
            <span className="text-cyan-300 font-extrabold">Key Architectural Takeaway:</span> Existing models → VARUNA → Better-informed operational decision-making.
          </div>
        </div>
      </section>

      {/* 6. 14-STAGE CANONICAL PIPELINE SECTION WITH VIDEO DEMO */}
      <section id="pipeline" className="py-24 px-4 bg-slate-950/95 border-t border-slate-900 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold">
              Scientific Processing Architecture
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow">
              FROM RAW FORECASTS TO FORECAST INTELLIGENCE
            </h2>
            <p className="text-sm font-mono text-slate-100 max-w-2xl mx-auto font-medium">
              Inspect the canonical 14-stage end-to-end pipeline that ingests, cleanses, evaluates, weights, fuses, and verifies forecasts in real-time.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left 14-Stage Interactive Scrubber List */}
            <div className="lg:col-span-5 space-y-2 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
              {pipelineStages.map((s, idx) => {
                const Icon = s.icon;
                const isActive = activeStage === idx + 1;
                return (
                  <button
                    key={s.num}
                    onClick={() => setActiveStage(idx + 1)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all flex items-start gap-3 ${
                      isActive
                        ? 'bg-[#0a2046] border-2 border-cyan-400 shadow-lg shadow-cyan-950/50'
                        : 'bg-[#0d172e] border-slate-700/80 hover:bg-slate-900 hover:border-cyan-500/40'
                    }`}
                  >
                    <span className={`text-xs font-mono font-extrabold px-2 py-1 rounded shrink-0 ${
                      isActive ? 'bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-200'
                    }`}>
                      {s.num}
                    </span>
                    <div>
                      <div className="flex items-center gap-2 font-bold text-sm text-white">
                        <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-cyan-300'}`} />
                        {s.title}
                      </div>
                      <p className="text-xs text-slate-200 font-mono mt-1 leading-relaxed font-medium">
                        {s.desc}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Right Video Showcase Canvas & Active Stage Display */}
            <div className="lg:col-span-7 bg-[#0d162a] border border-slate-700 rounded-2xl p-6 space-y-6 flex flex-col justify-between shadow-2xl">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-700 pb-3">
                  <span className="text-xs font-mono font-extrabold text-cyan-300 uppercase">
                    Pipeline Stage {activeStage} / 14: {pipelineStages[activeStage - 1].title}
                  </span>
                  <span className="text-xs font-mono font-bold text-cyan-200 bg-slate-800 border border-slate-700 px-2.5 py-0.5 rounded">
                    Operational Execution
                  </span>
                </div>

                <div className="relative rounded-xl overflow-hidden border-2 border-cyan-400/60 aspect-video shadow-2xl bg-black">
                  <video
                    autoPlay
                    loop
                    muted
                    playsInline
                    poster="/assets/varuna/screen.png"
                    className="w-full h-full object-cover"
                  >
                    <source src="/assets/varuna/showcase_video.mp4" type="video/mp4" />
                  </video>
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80" />
                  <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-xs font-mono font-bold text-white bg-slate-900/90 backdrop-blur border border-slate-700 p-3 rounded-lg shadow-md">
                    <span className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-cyan-400" />
                      Active: {pipelineStages[activeStage - 1].title}
                    </span>
                    <span className="text-xs text-cyan-300">Live Stage Renderer</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  disabled={activeStage === 1}
                  onClick={() => setActiveStage(prev => Math.max(1, prev - 1))}
                  className="px-4 py-2 text-xs font-mono font-bold text-white bg-slate-800 hover:bg-slate-700 border border-slate-600 disabled:opacity-40 rounded-lg"
                >
                  ← Previous Stage
                </button>
                <span className="text-xs font-mono font-bold text-slate-200">
                  Step {activeStage} of 14
                </span>
                <button
                  disabled={activeStage === 14}
                  onClick={() => setActiveStage(prev => Math.min(14, prev + 1))}
                  className="px-4 py-2 text-xs font-mono font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 border border-cyan-400 disabled:opacity-40 rounded-lg shadow-md"
                >
                  Next Stage →
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. ADAPTIVE TRUST SECTION (INTERACTIVE CONTEXT SIMULATOR) */}
      <section id="trust" className="py-24 px-4 bg-[#070c18] border-t border-slate-900 relative">
        <div className="max-w-6xl mx-auto space-y-16">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold">
              Dynamic Trust Allocation
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow">
              TRUST IS NOT STATIC.
            </h2>
            <p className="text-sm font-mono text-slate-100 max-w-2xl mx-auto font-medium">
              Simulate how VARUNA recalculates model weights dynamically as region, lead time, and weather regime shift.
            </p>
          </div>

          <div className="bg-[#0e1933] border-2 border-cyan-400/60 rounded-2xl p-6 sm:p-10 space-y-8 shadow-2xl relative">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700/80 pb-6">
              <div>
                <span className="text-xs font-mono text-cyan-300 uppercase font-extrabold">
                  Interactive Context Simulator
                </span>
                <h3 className="font-headline font-extrabold text-xl text-white">
                  Test Model Reliability Drift
                </h3>
              </div>
              <span className="text-xs font-mono font-bold text-amber-300 bg-amber-950/80 border border-amber-400/60 px-3 py-1 rounded">
                ILLUSTRATIVE DEMO — NOT OPERATIONAL FORECAST
              </span>
            </div>

            {/* Context Control Inputs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-mono text-slate-200 uppercase font-bold">Region Centroid</label>
                <select
                  value={simRegion}
                  onChange={(e) => setSimRegion(e.target.value)}
                  className="w-full bg-slate-950 border border-cyan-500/40 rounded-lg p-3 text-xs font-mono text-white font-bold outline-none focus:border-cyan-400 shadow-inner"
                >
                  <option value="TELANGANA">Telangana (Inland Convective)</option>
                  <option value="WESTERN_GHATS">Western Ghats (Orogaphic Monsoon)</option>
                  <option value="ODISHA">Odisha Coast (Cyclonic Depression)</option>
                  <option value="GENERIC">North-West Plains (General)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-mono text-slate-200 uppercase font-bold">Forecast Lead Time</label>
                <div className="grid grid-cols-3 gap-2">
                  {[24, 48, 72].map(hours => (
                    <button
                      key={hours}
                      onClick={() => setSimLead(hours)}
                      className={`p-3 text-xs font-mono font-bold rounded-lg border transition-all ${
                        simLead === hours
                          ? 'bg-cyan-400 text-slate-950 border-cyan-400 shadow-md'
                          : 'bg-slate-950 text-slate-200 border-slate-700 hover:text-white'
                      }`}
                    >
                      +{hours}h
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-mono text-slate-200 uppercase font-bold">Synoptic Weather Regime</label>
                <select
                  value={simRegime}
                  onChange={(e) => setSimRegime(e.target.value)}
                  className="w-full bg-slate-950 border border-cyan-500/40 rounded-lg p-3 text-xs font-mono text-white font-bold outline-none focus:border-cyan-400 shadow-inner"
                >
                  <option value="HEAVY_RAINFALL">Heavy Rainfall Event</option>
                  <option value="CONVECTIVE">Active Monsoon Trough</option>
                  <option value="NORMAL">Normal Seasonal Flow</option>
                </select>
              </div>
            </div>

            {/* Calculated Weight Bars Visualization */}
            <div className="space-y-6 pt-4">
              <div className="flex items-center justify-between text-xs font-mono text-slate-200 border-b border-slate-700/80 pb-2 font-bold">
                <span>Calculated Convex Weights (∑ w_i = 1.0)</span>
                <span className="text-cyan-300 font-extrabold text-sm">Fused Forecast: {simWeights.fused} mm</span>
              </div>

              <div className="space-y-4">
                {[
                  { name: 'NCUM 12km', w: simWeights.NCUM, color: 'bg-cyan-400' },
                  { name: 'WRF 3km', w: simWeights.WRF, color: 'bg-teal-400' },
                  { name: 'AI Weather Operator', w: simWeights.AI_WEATHER, color: 'bg-indigo-400' },
                  { name: 'NOAA GFS 25km', w: simWeights.GFS, color: 'bg-purple-400' },
                ].map((item) => (
                  <div key={item.name} className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-mono font-bold">
                      <span className="text-white">{item.name}</span>
                      <span className="text-cyan-200">{(item.w / 100).toFixed(2)} ({item.w}%)</span>
                    </div>
                    <div className="h-3.5 w-full bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-700">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${item.w}%` }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                        className={`h-full rounded-full ${item.color}`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 8. FORECAST FUSION SECTION */}
      <section id="fusion" className="py-24 px-4 bg-slate-950/90 border-t border-slate-900 relative">
        <div className="max-w-6xl mx-auto space-y-16">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold">
              Adaptive Synthesis
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow">
              DIFFERENT SIGNALS. ONE ADAPTIVE FORECAST.
            </h2>
            <p className="text-sm font-mono text-slate-100 max-w-2xl mx-auto font-medium">
              VARUNA does not simply average models. It conditions trust on context and learned reliability to synthesize an optimal forecast curve.
            </p>
          </div>

          <div className="bg-[#0e1933] border border-slate-700/80 rounded-2xl p-6 sm:p-10 space-y-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-700 pb-4">
              <span className="text-xs font-mono text-white uppercase font-bold">
                Fused Forecast Curve vs Input Ensemble Models
              </span>
              <span className="text-xs font-mono font-bold text-cyan-300 bg-slate-950 border border-cyan-400/60 px-3 py-1 rounded">
                Optimal Convex Combination: ∑ (w_i * F_i)
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center font-mono">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-700 shadow-md">
                <div className="text-xs text-slate-300 font-bold">NCUM PREDICTION</div>
                <div className="text-2xl font-bold text-cyan-300 mt-1">82.0 mm</div>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-700 shadow-md">
                <div className="text-xs text-slate-300 font-bold">GFS PREDICTION</div>
                <div className="text-2xl font-bold text-indigo-300 mt-1">103.0 mm</div>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-700 shadow-md">
                <div className="text-xs text-slate-300 font-bold">WRF PREDICTION</div>
                <div className="text-2xl font-bold text-teal-300 mt-1">47.0 mm</div>
              </div>
              <div className="bg-[#0a2046] p-4 rounded-xl border-2 border-cyan-400 shadow-xl">
                <div className="text-xs text-cyan-200 font-extrabold">VARUNA FUSED FORECAST</div>
                <div className="text-3xl font-black text-white mt-1 drop-shadow-md">70.1 mm</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 9. CLOSED-LOOP VERIFICATION LOOP */}
      <section id="verification" className="py-24 px-4 bg-[#070c18] border-t border-slate-900 relative">
        <div className="max-w-6xl mx-auto space-y-16">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold">
              Continuous Learning Feedback Loop
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow">
              EVERY FORECAST LEARNS FROM WHAT HAPPENED NEXT.
            </h2>
            <p className="text-sm font-mono text-slate-100 max-w-2xl mx-auto font-medium">
              VARUNA evaluates post-event ground truth against past predictions to continuously recalibrate model trust memory.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { step: "01", title: "Forecast Issued", desc: "Generates convex combination & confidence envelopes.", color: "border-cyan-400/60 text-cyan-300" },
              { step: "02", title: "Ground Observation", desc: "Ingests post-event AWS & Doppler observations.", color: "border-blue-400/60 text-blue-300" },
              { step: "03", title: "Error Calculated", desc: "Computes MAE, RMSE, and CRPS scores per model.", color: "border-purple-400/60 text-purple-300" },
              { step: "04", title: "Skill Memory Updated", desc: "Updates ModelSkill DB using Exponential Moving Average.", color: "border-teal-400/60 text-teal-300" },
              { step: "05", title: "Next Cycle Recalibrated", desc: "Refines meta-model weighting for subsequent runs.", color: "border-emerald-400/60 text-emerald-300" }
            ].map((st) => (
              <div key={st.step} className={`bg-[#0d162a] border ${st.color.split(' ')[0]} rounded-xl p-5 space-y-3 relative shadow-md`}>
                <div className="text-xs font-mono font-extrabold text-white">Step {st.step}</div>
                <h3 className={`font-bold text-sm ${st.color.split(' ')[1]}`}>{st.title}</h3>
                <p className="text-xs font-mono text-slate-200 leading-relaxed font-medium">{st.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 10. SYSTEM COMPARISON & PRODUCT MEDIA SECTION */}
      <section className="py-24 px-4 bg-slate-950/95 border-t border-slate-900 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold">
              Operational Visual Canvas
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow">
              SEE THE FORECAST INTELLIGENCE CANVAS
            </h2>
            <p className="text-sm font-mono text-slate-100 max-w-2xl mx-auto font-medium">
              Real-time spatial weight maps, hazard alerts, and explainable decision paths in action.
            </p>
          </div>

          <div className="rounded-2xl overflow-hidden border-2 border-cyan-400/60 aspect-video shadow-2xl relative bg-black">
            <video
              autoPlay
              loop
              muted
              playsInline
              poster="/assets/varuna/screen.png"
              className="w-full h-full object-cover"
            >
              <source src="/assets/varuna/scientic_visual_video.mp4" type="video/mp4" />
            </video>
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80" />
            <div className="absolute bottom-6 left-6 right-6 flex flex-wrap items-center justify-between gap-4 text-xs font-mono font-bold text-white bg-slate-900/90 backdrop-blur border border-slate-700 p-4 rounded-xl shadow-lg">
              <div>
                <span className="font-extrabold text-cyan-300">VARUNA Control Room Canvas</span> — Operational Spatial Weight Rendering
              </div>
              <button
                onClick={onOpenLogin}
                className="px-5 py-2 text-xs font-mono font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-full shadow-md"
              >
                Launch Dashboard →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 11. ROLE-BASED OPERATIONAL ENTRY */}
      <section className="py-24 px-4 bg-[#070c18] border-t border-slate-900 relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-300 font-bold">
              Institutional Access Portals
            </span>
            <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white drop-shadow">
              DESIGNED FOR OPERATIONAL ROLES
            </h2>
            <p className="text-sm font-mono text-slate-100 max-w-2xl mx-auto font-medium">
              Select your institutional role to enter the authenticated decision-support dashboard.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { role: 'FORECASTER', title: 'Forecaster Portal', color: 'border-emerald-400/60 text-emerald-300', desc: 'Review blended forecasts, confidence envelopes & SHAP drivers.' },
              { role: 'OPERATIONS', title: 'Operations Officer', color: 'border-blue-400/60 text-blue-300', desc: 'Monitor source feed dropouts, data quality & ingestion status.' },
              { role: 'ANALYST', title: 'Model Analyst', color: 'border-purple-400/60 text-purple-300', desc: 'Inspect historical skill curves, MAE drift & failure memory.' },
              { role: 'ADMIN', title: 'Administrator', color: 'border-amber-400/60 text-amber-300', desc: 'Audit system provenance, model governance & user permissions.' },
            ].map(r => (
              <div key={r.role} className={`bg-[#0d162a] border ${r.color.split(' ')[0]} rounded-xl p-6 space-y-4 flex flex-col justify-between shadow-xl`}>
                <div className="space-y-2">
                  <span className={`text-[10px] font-mono uppercase font-extrabold ${r.color.split(' ')[1]}`}>{r.role}</span>
                  <h3 className="font-headline font-extrabold text-lg text-white">{r.title}</h3>
                  <p className="text-xs font-mono text-slate-200 leading-relaxed font-medium">{r.desc}</p>
                </div>
                <button
                  onClick={onOpenLogin}
                  className="w-full py-2.5 text-xs font-mono font-extrabold text-white hover:text-cyan-300 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg transition-colors shadow-sm"
                >
                  Enter Portal →
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 12. FINAL CINEMATIC CTA */}
      <section className="py-28 px-4 bg-gradient-to-b from-[#070c18] via-slate-950 to-[#070c18] border-t border-slate-900 text-center relative overflow-hidden">
        <div className="max-w-4xl mx-auto space-y-8 relative z-10">
          <h2 className="font-headline font-extrabold text-3xl sm:text-5xl text-white leading-tight drop-shadow-md">
            WEATHER MODELS WILL ALWAYS DISAGREE. <br />
            <span className="text-cyan-300">THE QUESTION IS HOW INTELLIGENTLY WE RESPOND.</span>
          </h2>
          <p className="text-base sm:text-lg text-slate-100 font-mono font-bold max-w-2xl mx-auto">
            We don’t replace weather models. We make their strengths work together intelligently.
          </p>
          <div className="pt-4 flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={onOpenLogin}
              className="px-8 py-4 text-xs font-mono font-extrabold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-full shadow-2xl shadow-cyan-500/40 transition-all transform hover:scale-105"
            >
              ENTER VARUNA PLATFORM
            </button>
          </div>
        </div>
      </section>

      {/* 13. INSTITUTIONAL FOOTER */}
      <footer className="w-full bg-slate-950 border-t border-slate-900 px-6 py-8 text-xs font-mono text-slate-200 font-medium">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center md:text-left">
            <div className="font-headline font-extrabold text-white text-base flex items-center gap-2 justify-center md:justify-start">
              VARUNA — Adaptive Forecast Intelligence Platform
            </div>
            <div className="text-xs text-slate-300 font-semibold">
              SIH26081 • Ministry of Earth Sciences (MoES) / NCMRWF Prototype
            </div>
          </div>

          <div className="text-xs text-slate-300 font-medium max-w-md text-center md:text-right leading-relaxed">
            VARUNA is designed as a decision-support and forecast-intelligence layer. It does not replace official meteorological forecasts, warnings, or institutional decision authority.
          </div>
        </div>
      </footer>

    </div>
  );
};
