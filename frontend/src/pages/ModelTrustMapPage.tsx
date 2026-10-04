import React, { useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { 
  Sparkles, 
  Layers, 
  Maximize2, 
  Info, 
  MapPin, 
  Radio, 
  CheckCircle2, 
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  Crosshair
} from 'lucide-react';

export const ModelTrustMapPage: React.FC = () => {
  const { 
    subdivisions, 
    regionId, 
    setRegionId, 
    leadHours, 
    weatherRegime,
    setSelectedSubdivision,
    setIsDemoModalOpen,
    summary
  } = useVaruna();

  const [activeLayer, setActiveLayer] = useState<'dominant' | 'intensity' | 'spread' | 'forcing'>('dominant');
  const [modelFilter, setModelFilter] = useState<string>('all');
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  const selectedSub = subdivisions.find(s => s.id === regionId) || subdivisions[0];

  return (
    <div className="flex flex-col w-full animate-fadeIn pb-10">
      
      {/* Top Filter & HUD Strip */}
      <div className="p-4 lg:p-6 pb-0 flex flex-col gap-3">
        <div className="bg-surface-container-lowest p-3.5 rounded-xl border border-outline-variant/30 shadow-xs flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setActiveLayer('dominant')}
              className={`px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                activeLayer === 'dominant' ? 'bg-primary text-on-primary shadow-xs' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Dominant Model
            </button>
            <button
              onClick={() => setActiveLayer('intensity')}
              className={`px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                activeLayer === 'intensity' ? 'bg-primary text-on-primary shadow-xs' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Trust Intensity
            </button>
            <button
              onClick={() => setActiveLayer('spread')}
              className={`px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                activeLayer === 'spread' ? 'bg-primary text-on-primary shadow-xs' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Disagreement Spread
            </button>
            <button
              onClick={() => setActiveLayer('forcing')}
              className={`px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                activeLayer === 'forcing' ? 'bg-primary text-on-primary shadow-xs' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Synoptic Forcing
            </button>

            <span className="text-outline-variant hidden md:inline">|</span>

            <div className="flex items-center gap-1.5 text-xs font-mono text-on-surface-variant">
              <span>MODEL FILTER:</span>
              <select 
                value={modelFilter}
                onChange={(e) => setModelFilter(e.target.value)}
                className="bg-surface-container-low border border-outline-variant/40 rounded px-2 py-1 text-xs text-on-surface font-semibold focus:outline-none"
              >
                <option value="all">Ensemble Consensus & Dominant</option>
                <option value="ncum">NCUM Only</option>
                <option value="wrf">WRF-ARW Only</option>
                <option value="ai">VARUNA-AI Only</option>
                <option value="gfs">GFS Only</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-on-surface-variant bg-surface-container-low px-2 py-1 rounded">
              INITIALIZED: 00Z SYNTHETIC STRESS BENCHMARK
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-secondary-fixed text-on-secondary-fixed font-mono text-[11px] font-bold">
              <Sparkles className="w-3 h-3 text-secondary" />
              PHYSICS-INFORMED DEMO MAP
            </span>
          </div>
        </div>
      </div>

      {/* Main Map Split Workspace */}
      <div className="p-4 lg:p-6 grid grid-cols-1 xl:grid-cols-12 gap-5">
        
        {/* Left Map Viewport (8 Cols) */}
        <div className="xl:col-span-8 flex flex-col gap-3">
          <div className="relative bg-[#eef4f9] dark:bg-[#070d1a] rounded-xl border border-outline-variant/30 shadow-md overflow-hidden flex flex-col min-h-[520px] lg:min-h-[580px] xl:min-h-[620px]">
            
            {/* Map Canvas Header Coordinates HUD */}
            <div className="px-4 py-2 bg-surface-container-lowest/90 backdrop-blur-md flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-on-surface-variant border-b border-outline-variant/30 z-10">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-primary font-bold">
                  <Crosshair className="w-3.5 h-3.5" /> 17.8443° N, 79.1129° E
                </span>
                <span>EPSG:4326</span>
                <span className="px-1.5 py-0.2 rounded bg-surface-container-high text-on-surface font-semibold">
                  RES: 0.05°
                </span>
              </div>
              <span className="text-on-surface-variant">LAT: 8°N-36°N • LON: 68°E-96°E</span>
            </div>

            {/* Floating Zoom Controls */}
            <div className="absolute top-14 right-4 z-20 flex flex-col gap-1 bg-surface-container-lowest/95 backdrop-blur rounded shadow-sm border border-outline-variant/30 p-1">
              <button 
                onClick={() => setZoomLevel(prev => Math.min(prev + 0.15, 1.6))}
                className="p-1.5 hover:bg-surface-container-high rounded text-on-surface"
                title="Zoom in"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button 
                onClick={() => setZoomLevel(prev => Math.max(prev - 0.15, 0.85))}
                className="p-1.5 hover:bg-surface-container-high rounded text-on-surface"
                title="Zoom out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button 
                onClick={() => setZoomLevel(1)}
                className="p-1.5 hover:bg-surface-container-high rounded text-on-surface"
                title="Reset zoom"
              >
                <Crosshair className="w-4 h-4" />
              </button>
            </div>

            {/* RECOGNIZABLE GEOGRAPHIC INDIA SVG MAP */}
            <div className="w-full flex-1 relative flex items-center justify-center overflow-hidden p-2">
              <svg 
                className="w-full h-full max-h-[640px] select-none transition-transform duration-300" 
                style={{ transform: `scale(${zoomLevel})` }}
                fill="none" 
                viewBox="0 0 950 900" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  {/* Disagreement Orange Diagonal Crosshatch Pattern */}
                  <pattern height="10" id="severeDisagreementHatch" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse" width="10">
                    <line stroke="#f59e0b" strokeOpacity="0.85" strokeWidth="2.5" x1="0" x2="0" y1="0" y2="10" />
                    <rect fill="#fef3c7" fillOpacity="0.35" height="10" width="10" />
                  </pattern>
                  {/* Glowing Filter for Selected Zone */}
                  <filter height="140%" id="activeSubdivGlow" width="140%" x="-20%" y="-20%">
                    <feDropShadow dx="0" dy="0" floodColor="#0284c7" floodOpacity="0.6" stdDeviation="6" />
                  </filter>
                </defs>

                {/* Marine Basin Base */}
                <rect className="fill-[#f1f6fa] dark:fill-[#070d1a]" height="900" width="950" />

                {/* LATITUDE & LONGITUDE SCIENTIFIC GRATICULES */}
                <g className="stroke-[#cbd5e1] dark:stroke-[#1b2a47]" strokeDasharray="3 4" strokeWidth="0.7">
                  <line x1="40" x2="910" y1="130" y2="130" />
                  <line x1="40" x2="910" y1="260" y2="260" />
                  <line x1="40" x2="910" y1="390" y2="390" />
                  <line x1="40" x2="910" y1="520" y2="520" />
                  <line x1="40" x2="910" y1="650" y2="650" />
                  <line x1="40" x2="910" y1="780" y2="780" />
                  <line x1="160" x2="160" y1="40" y2="860" />
                  <line x1="290" x2="290" y1="40" y2="860" />
                  <line x1="420" x2="420" y1="40" y2="860" />
                  <line x1="550" x2="550" y1="40" y2="860" />
                  <line x1="680" x2="680" y1="40" y2="860" />
                  <line x1="810" x2="810" y1="40" y2="860" />
                </g>

                {/* Graticule Labels */}
                <g className="fill-slate-400 font-mono text-[9px] tracking-wider" opacity="0.8">
                  <text x="50" y="126">32° N</text>
                  <text x="50" y="256">28° N</text>
                  <text x="50" y="386">24° N</text>
                  <text x="50" y="516">20° N</text>
                  <text x="50" y="646">16° N</text>
                  <text x="50" y="776">12° N</text>
                  <text x="164" y="875">72° E</text>
                  <text x="294" y="875">76° E</text>
                  <text x="424" y="875">80° E</text>
                  <text x="554" y="875">84° E</text>
                  <text x="684" y="875">88° E</text>
                  <text x="814" y="875">92° E</text>
                </g>

                {/* Surrounding Waters Labels */}
                <text className="fill-slate-400 font-mono text-[11px] uppercase tracking-widest font-semibold" x="100" y="660">Arabian Sea</text>
                <text className="fill-slate-400 font-mono text-[11px] uppercase tracking-widest font-semibold" x="680" y="650">Bay of Bengal</text>
                <text className="fill-slate-400 font-mono text-[10px] uppercase tracking-widest font-semibold" x="360" y="870">Indian Ocean Equatorial Region</text>

                {/* 1. Northern: Jammu & Kashmir / Ladakh */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('himalayas')}>
                  <polygon fill="#e2e8f0" points="310,50 365,65 385,100 370,145 320,150 280,115 285,75" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-slate-600 font-headline text-[10px] font-bold" x="305" y="105">J&amp;K / LADAKH</text>
                  <text className="fill-slate-500 font-mono text-[8px]" x="312" y="118">NCUM REGIONAL</text>
                </g>

                {/* 2. Northern: Punjab & Himachal */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('punjab')}>
                  <polygon fill="#e0f2fe" points="275,120 320,150 340,195 295,215 260,180 265,145" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-sky-800 font-headline text-[10px] font-bold" x="272" y="170">PUNJAB &amp; HP</text>
                  <text className="fill-sky-600 font-mono text-[8px]" x="280" y="182">WRF REGIONAL</text>
                </g>

                {/* 3. Northern: Western Rajasthan */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('rajasthan')}>
                  <polygon fill="#f1f5f9" points="200,205 260,180 290,215 265,305 185,310 170,240" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-slate-700 font-headline text-[10px] font-bold" x="200" y="250">W. RAJASTHAN</text>
                  <text className="fill-slate-500 font-mono text-[8px]" x="208" y="263">GFS GLOBAL</text>
                </g>

                {/* 4. Central & West: Gujarat & Saurashtra */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('saurashtra')}>
                  <polygon fill="#c0c1ff" points="120,345 190,320 225,355 240,410 195,435 140,410 115,370" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-[#2f2ebe] font-headline text-[10px] font-bold" x="145" y="380">GUJARAT &amp; SAU</text>
                  <text className="fill-[#4648d4] font-mono text-[9px] font-semibold" x="148" y="393">VARUNA-AI</text>
                </g>

                {/* 5. Central: Madhya Pradesh & Vidarbha */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('west_mp')}>
                  <polygon fill="#bae6fd" points="265,305 380,270 450,305 450,400 370,425 285,415 240,360" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-sky-900 font-headline text-[11px] font-bold" x="320" y="345">MADHYA PRADESH</text>
                  <text className="fill-sky-700 font-mono text-[9px] font-semibold" x="335" y="360">NCUM REGIONAL</text>
                </g>

                {/* 6. East: Gangetic West Bengal & Bihar */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('gangetic_wb')}>
                  <polygon fill="#e0f2fe" points="380,270 550,250 595,290 560,380 470,360 450,305" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-sky-900 font-headline text-[10px] font-bold" x="470" y="305">GANGETIC BENGAL</text>
                  <text className="fill-sky-700 font-mono text-[8px]" x="495" y="318">NCUM REGIONAL</text>
                </g>

                {/* 7. North-East: Assam & Meghalaya */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('assam')}>
                  <polygon fill="#bae6fd" points="620,240 730,210 780,250 740,320 670,310 635,270" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-sky-900 font-headline text-[10px] font-bold" x="660" y="270">ASSAM / MEG</text>
                  <text className="fill-sky-700 font-mono text-[8px] font-medium" x="670" y="283">NCUM REGIONAL</text>
                </g>

                {/* 8. West Coastal: Maharashtra & Konkan */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('konkan')}>
                  <polygon fill="#39b8fd" points="225,435 305,420 360,455 330,555 255,540 220,490" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-[#003852] font-headline text-[10px] font-bold" x="245" y="480">KONKAN &amp; MH</text>
                  <text className="fill-[#004c6e] font-mono text-[8px] font-semibold" x="248" y="494">WRF REGIONAL</text>
                </g>

                {/* 9. East Coast: ODISHA (Severe Disagreement Zone - Amber Hatch) */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('odisha')}>
                  <polygon fill="url(#severeDisagreementHatch)" points="460,390 560,375 600,430 545,510 470,480 445,435" stroke="#f59e0b" strokeWidth="2" />
                  <circle cx="525" cy="445" fill="#f59e0b" opacity="0.6" r="5" />
                  <circle cx="525" cy="445" fill="#d97706" r="3.5" />
                  <rect fill="#ffffff" fillOpacity="0.9" height="24" rx="2" stroke="#f59e0b" strokeWidth="0.8" width="110" x="470" y="455" />
                  <text className="fill-amber-900 font-headline text-[9px] font-bold" x="476" y="468">ODISHA COAST</text>
                  <text className="fill-rose-700 font-mono text-[8px] font-bold" x="476" y="476">DISAGREEMENT ZONE</text>
                </g>

                {/* 10. ACTIVE FOCUS: TELANGANA METEOROLOGICAL SUB-DIVISION */}
                <g className="cursor-pointer" onClick={() => setRegionId('telangana')}>
                  <polygon 
                    fill="#0284c7" 
                    fillOpacity="0.82" 
                    filter="url(#activeSubdivGlow)" 
                    points="345,475 440,450 475,520 420,605 345,565" 
                    stroke="#0369a1" 
                    strokeWidth="3.2" 
                  />
                  {/* Pulsing Station Reticle */}
                  <g transform="translate(400, 530)">
                    <circle className="animate-spin" cx="0" cy="0" fill="none" r="18" stroke="#ffffff" strokeDasharray="2 3" strokeWidth="1.2" style={{ animationDuration: '8s' }} />
                    <circle cx="0" cy="0" fill="none" r="10" stroke="#38bdf8" strokeWidth="1.5" />
                    <circle cx="0" cy="0" fill="#ffffff" r="4" />
                    <circle cx="0" cy="0" fill="#0284c7" r="2" />
                    <line stroke="#ffffff" strokeWidth="1" x1="-14" x2="14" y1="0" y2="0" />
                    <line stroke="#ffffff" strokeWidth="1" x1="0" x2="0" y1="-14" y2="14" />
                  </g>
                  {/* Name Tag */}
                  <rect fill="#001d31" fillOpacity="0.95" height="32" rx="3" stroke="#93ccff" strokeWidth="1" width="140" x="345" y="555" />
                  <text className="fill-sky-200 font-headline text-[10px] font-bold" x="350" y="569">{selectedSub.name.toUpperCase()}</text>
                  <text className="fill-white font-mono text-[9px] font-medium" x="350" y="581">
                    {summary?.weights ? `DOMINANT: ${Math.round(Math.max(...summary.weights.map(x=>x.weight)) * 100)}%` : 'DOMINANT MODEL'}
                  </text>
                </g>

                {/* 11. South East: Coastal Andhra & Rayalaseema */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('coastal_ap')}>
                  <polygon fill="#bae6fd" points="420,605 475,520 545,510 500,670 435,665 395,620" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-sky-900 font-headline text-[10px] font-bold" x="440" y="600">ANDHRA &amp; RAYAL</text>
                  <text className="fill-sky-700 font-mono text-[8px]" x="450" y="612">NCUM REGIONAL</text>
                </g>

                {/* 12. South West: Karnataka */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('coastal_karnataka')}>
                  <polygon fill="#e0f2fe" points="275,550 345,565 395,620 375,700 295,670" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-sky-900 font-headline text-[10px] font-bold" x="305" y="615">KARNATAKA</text>
                  <text className="fill-sky-700 font-mono text-[8px]" x="312" y="628">WRF REGIONAL</text>
                </g>

                {/* 13. Southern Tip: Tamil Nadu */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('tamil_nadu')}>
                  <polygon fill="#e2e8f0" points="375,700 440,665 435,770 365,820 345,770" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-slate-700 font-headline text-[10px] font-bold" x="370" y="745">TAMIL NADU</text>
                  <text className="fill-slate-500 font-mono text-[8px]" x="375" y="758">GFS GLOBAL</text>
                </g>

                {/* 14. South West: Kerala */}
                <g className="cursor-pointer subdiv-hover" onClick={() => setRegionId('kerala')}>
                  <polygon fill="#39b8fd" points="295,670 345,770 365,820 325,830 290,750" stroke="#ffffff" strokeWidth="1.8" />
                  <text className="fill-[#003852] font-headline text-[10px] font-bold" x="270" y="785">KERALA</text>
                  <text className="fill-[#004c6e] font-mono text-[8px] font-bold" x="270" y="798">WRF REGIONAL</text>
                </g>

                {/* Peninsular Station Dots */}
                <g fill="#10b981" stroke="#ffffff" strokeWidth="1">
                  <circle cx="380" cy="510" r="2.5" />
                  <circle cx="430" cy="500" r="2.5" />
                  <circle cx="360" cy="540" r="2.5" />
                  <circle cx="440" cy="560" r="2.5" />
                  <circle cx="395" cy="580" r="2.5" />
                  <circle cx="320" cy="460" r="2.5" />
                  <circle cx="505" cy="430" r="2.5" />
                  <circle cx="330" cy="730" r="2.5" />
                </g>

                {/* Rain Isohyet Streamlines */}
                <g fill="none" opacity="0.65" stroke="#0284c7">
                  <path d="M 330,500 C 370,520 410,510 460,490" strokeDasharray="4 4" strokeWidth="2" />
                  <path d="M 340,540 C 380,560 420,550 480,520" strokeDasharray="6 3" strokeWidth="2.5" />
                  <path d="M 350,580 C 390,600 440,580 500,550" strokeDasharray="3 3" strokeWidth="1.8" />
                </g>
              </svg>

              {/* Anchored Tooltip over Selected Zone */}
              <div className="absolute left-[47%] top-[45%] -translate-x-1/2 -translate-y-full mb-3 pointer-events-none z-30">
                <div className="bg-slate-900/95 text-white px-3 py-2 rounded shadow-xl border-l-3 border-sky-400 backdrop-blur-xs flex flex-col gap-0.5 min-w-[190px]">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono text-[9px] text-primary uppercase tracking-wider font-semibold">{selectedSub.name.toUpperCase()} TARGET</span>
                    <span className="font-mono text-[9px] text-on-surface-variant">+{leadHours}H LEAD</span>
                  </div>
                  <div className="flex items-baseline justify-between mt-0.5">
                    <div className="flex items-baseline gap-1">
                      <span className="font-headline text-xl font-bold text-white leading-none">{summary?.fused_forecast ?? 'N/A'}</span>
                      <span className="font-body text-xs text-on-surface-variant">{summary?.unit || 'mm'}</span>
                    </div>
                    <span className="px-1.5 py-0.2 rounded bg-sky-500/20 text-primary font-mono text-[9px] font-bold border border-sky-400/30">
                      {summary?.weights ? `DOMINANT: ${Math.round(Math.max(...summary.weights.map(x => x.weight)) * 100)}%` : 'DOMINANT'}
                    </span>
                  </div>
                </div>
                <div className="w-2 h-2 bg-slate-900/95 rotate-45 mx-auto -mt-1" />
              </div>
            </div>

            {/* Comprehensive Dynamic Legend Dock */}
            <div className="absolute right-3 bottom-3 z-20 bg-white/95 backdrop-blur-md p-2.5 rounded-lg shadow-md border border-slate-200 flex flex-col gap-1.5 min-w-[280px]">
              <div className="flex items-center justify-between border-b border-slate-200 pb-1">
                <span className="font-mono text-[10px] uppercase font-bold text-slate-700 tracking-wider">
                  Model Trust Weights
                </span>
                <span className="font-mono text-[9px] text-on-surface-variant">+{leadHours}H LEAD</span>
              </div>
              <div className="grid grid-cols-2 gap-1.5 text-xs font-mono">
                {summary && summary.weights ? (
                  summary.weights.map(w => (
                    <div key={w.model_id} className="flex items-center gap-1.5">
                      <span className={`w-2.5 h-2.5 rounded ${
                        w.model_id === 'NCUM' ? 'bg-[#006194]' : 
                        w.model_id === 'WRF' ? 'bg-[#39b8fd]' : 
                        w.model_id === 'AI_WEATHER' ? 'bg-[#c0c1ff]' : 'bg-[#e2e8f0]'
                      }`} />
                      <span className="text-slate-700">{w.model_id} ({Math.round(w.weight * 100)}%)</span>
                    </div>
                  ))
                ) : (
                  <span className="text-slate-500 text-[10px]">Loading model weights...</span>
                )}
              </div>
              <div className="pt-1 border-t border-slate-100 flex items-center gap-1.5 font-mono text-[10px] text-amber-700">
                <span className="w-2.5 h-2.5 border border-amber-500 bg-amber-100" />
                <span>Inter-Model Disagreement Zone</span>
              </div>
            </div>

            {/* Bottom Status Bar */}
            <div className="px-4 py-2 bg-surface-container-lowest flex items-center justify-between text-xs font-mono text-on-surface-variant border-t border-outline-variant/30">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-primary" />
                <span>MAP MODE: ADAPTIVE TRUST MAP • CONTROLLED SYNTHETIC BENCHMARK</span>
              </div>
              <span className="text-on-surface-variant">RFC 7946 GeoJSON Standard</span>
            </div>
          </div>
        </div>

        {/* Right Detail Panel (4 Cols) */}
        <div className="xl:col-span-4 flex flex-col gap-4">
          
          {/* Header Card */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-outline-variant/30 flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-primary font-bold">● SELECTED SUB-DIVISION</span>
              <span className="text-on-surface-variant">ID: {selectedSub.id}</span>
            </div>
            <h2 className="font-headline font-bold text-xl text-on-surface tracking-tight">
              {selectedSub.name.toUpperCase()} SUB-DIVISION
            </h2>
            <div className="text-xs font-mono text-on-surface-variant">
              COORDS: {selectedSub.centroid?.lat || 17.84}°N, {selectedSub.centroid?.lon || 79.11}°E
            </div>
            <div className="flex items-center gap-1.5 text-xs text-primary font-mono bg-surface-container-low p-2 rounded">
              <Radio className="w-3.5 h-3.5" />
              <span>Observation Stream: NOT_VERIFIED (Operational Sensor Feed Unavailable)</span>
            </div>
          </div>

          {/* Fused Forecast Card */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-outline-variant/30 flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-on-surface-variant font-semibold">FUSED FORECAST ({leadHours}H LEAD)</span>
              <span className="px-2 py-0.5 rounded bg-secondary-fixed text-on-secondary-fixed font-bold text-[11px]">
                ● {summary?.uncertainty?.confidence || 'MEDIUM'} CONFIDENCE
              </span>
            </div>
            <div className="flex items-baseline justify-between mt-1">
              <div className="flex items-baseline gap-1">
                <span className="font-data-display font-extrabold text-4xl text-on-surface">{summary?.fused_forecast ?? 'N/A'}</span>
                <span className="font-headline text-sm font-semibold text-primary">{summary?.unit || 'mm'}</span>
              </div>
              <div className="text-right font-mono text-xs text-error font-semibold">
                <div>ENSEMBLE SPREAD</div>
                <div className="text-sm">
                  {summary?.disagreement?.forecast_spread ? `±${(summary.disagreement.forecast_spread / 2).toFixed(1)} ${summary.unit}` : 'SPREAD N/A'}
                </div>
              </div>
            </div>
            <div className="pt-2 flex justify-between font-mono text-[10px] text-on-surface-variant border-t border-outline-variant/20">
              <span>Min: {summary?.model_forecasts ? Math.min(...Object.values(summary.model_forecasts)) : 'N/A'} {summary?.unit || 'mm'}</span>
              <span className="text-primary font-bold">Fused: {summary?.fused_forecast} {summary?.unit || 'mm'}</span>
              <span>Max: {summary?.model_forecasts ? Math.max(...Object.values(summary.model_forecasts)) : 'N/A'} {summary?.unit || 'mm'}</span>
            </div>
          </div>

          {/* Dynamic Model Allocation Card */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-outline-variant/30 flex flex-col gap-2.5">
            <div className="flex items-center justify-between text-xs font-mono border-b border-outline-variant/20 pb-1.5">
              <span className="text-on-surface font-bold">DYNAMIC MODEL ALLOCATION</span>
              <span className="text-primary font-bold">SYNTHESIS ENGINE</span>
            </div>
            
            <div className="flex flex-col gap-2">
              {summary && summary.weights ? (
                // BUGFIX: `weights` is an array of {model_id, weight}; Object.entries() produced
                // keys "0".."3" and NaN% for every row.
                summary.weights.map((wItem) => [wItem.model_id, wItem.weight] as [string, number]).map(([modelKey, val]) => {
                  const weightVal = Number(val);
                  const maxWeight = Math.max(...summary.weights.map(v => Number(v.weight)));
                  const pct = Math.round(weightVal * 100);
                  const isDominant = weightVal === maxWeight;
                  let label = modelKey.toUpperCase();
                  if (modelKey === 'NCUM' || modelKey === 'ncum') label = 'NCUM-Global (12km)';
                  if (modelKey === 'WRF' || modelKey === 'wrf') label = 'WRF-ARW Regional (3km)';
                  if (modelKey === 'AI_WEATHER' || modelKey === 'ai') label = 'AI Weather Model (0.25°)';
                  if (modelKey === 'GFS' || modelKey === 'gfs') label = 'GFS-Operational (0.25° / ~25 km)';

                  return (
                    <div key={modelKey} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5 font-semibold text-on-surface">
                          <span className={`w-2 h-2 rounded-full ${isDominant ? 'bg-primary' : 'bg-secondary'}`} />
                          <span>{label}</span>
                          {isDominant && (
                            <span className="px-1.5 py-0.2 rounded bg-primary-fixed text-on-primary-fixed text-[9px] font-mono font-bold">
                              DOMINANT
                            </span>
                          )}
                        </div>
                        <span className="font-mono font-bold text-sm text-primary">{pct}%</span>
                      </div>
                      <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                        <div className="bg-primary h-full rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs font-mono text-on-surface-variant">No model weights loaded.</div>
              )}
            </div>
          </div>

          {/* Explanatory Panel: Model Reweighting Drivers */}
          <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-outline-variant/30 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="font-headline font-bold text-xs text-on-surface flex items-center gap-1">
                <Info className="w-3.5 h-3.5 text-primary" /> WHY ARE WEIGHTS ADJUSTED HERE?
              </span>
              <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-mono text-[10px] font-bold">
                DYNAMIC ADAPTATION
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-2 rounded bg-surface-container-low flex items-start gap-2">
                <span className="px-1.5 py-0.5 rounded bg-error-container text-on-error-container font-mono text-[10px] font-bold shrink-0">
                  BIAS CLAMP
                </span>
                <p className="text-on-surface-variant text-[11px] leading-relaxed">
                  <strong className="text-on-surface">Historical Bias Offset:</strong> WRF exhibits systematic positive moisture accumulation bias under heavy convective regimes in benchmark evaluations.
                </p>
              </div>

              <div className="p-2 rounded bg-surface-container-low flex items-start gap-2">
                <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 font-mono text-[10px] font-bold shrink-0">
                  LEAD DRIFT
                </span>
                <p className="text-on-surface-variant text-[11px] leading-relaxed">
                  <strong className="text-on-surface">Lead-Time Decay:</strong> Verification error penalization applied across extended lead horizons (+48h / +72h).
                </p>
              </div>

              <div className="p-2 rounded bg-surface-container-low flex items-start gap-2">
                <span className="px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface font-mono text-[10px] font-bold shrink-0">
                  DISAGREEMENT
                </span>
                <p className="text-on-surface-variant text-[11px] leading-relaxed">
                  <strong className="text-on-surface">Inter-Model Variance:</strong> GFS forecast divergence penalizes coarse global model weights during localized convective events.
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
