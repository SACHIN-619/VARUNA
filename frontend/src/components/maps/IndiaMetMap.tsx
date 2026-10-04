import React, { useState } from 'react';
import { IndianSubdivision, ModelId } from '../../types';
import { useVaruna } from '../../context/VarunaContext';
import { fallbackSubdivisions } from '../../services/api';
import { Layers, Compass, ZoomIn, ZoomOut, RotateCcw, Sparkles } from 'lucide-react';
import { ProvenanceBadge } from '../shared/ProvenanceBadge';

export type MapLayer = 'dominant' | 'trust' | 'disagreement' | 'confidence' | 'rainfall';

interface IndiaMetMapProps {
  onSelectSubdivision?: (sub: IndianSubdivision) => void;
  heightClass?: string;
  showControls?: boolean;
}

export const IndiaMetMap: React.FC<IndiaMetMapProps> = ({
  onSelectSubdivision,
  heightClass = 'min-h-[580px]',
  showControls = true
}) => {
  const { subdivisions, regionId, setRegionId, setSelectedSubdivision } = useVaruna();
  const [activeLayer, setActiveLayer] = useState<MapLayer>('dominant');
  const [hoveredSub, setHoveredSub] = useState<IndianSubdivision | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const getSub = (index: number): IndianSubdivision => {
    return (subdivisions && subdivisions[index]) || fallbackSubdivisions[index] || fallbackSubdivisions[0];
  };

  // Region labels are derived from the live subdivision data (they were hard-coded strings)
  const subLabel = (sub?: IndianSubdivision, long = false): string => {
    if (!sub) return '';
    const m = sub.dominant_model === 'AI_WEATHER' ? 'AI' : sub.dominant_model;
    return long ? `${m} DOMINANT: ${sub.trust_percentage}%` : `${m} (${sub.trust_percentage}%)`;
  };

  const handleSubClick = (sub: IndianSubdivision) => {
    if (!sub) return;
    setRegionId(sub.id);
    setSelectedSubdivision(sub);
    if (onSelectSubdivision) onSelectSubdivision(sub);
  };

  const getSubColor = (sub: IndianSubdivision) => {
    if (!sub) return '#1e293b';
    const isSelected = sub.id === regionId;

    if (activeLayer === 'dominant') {
      switch (sub.dominant_model) {
        case 'NCUM':
          return isSelected ? '#00e5ff' : '#0284c7';
        case 'WRF':
          return isSelected ? '#34d399' : '#059669';
        case 'AI_WEATHER':
          return isSelected ? '#a78bfa' : '#6366f1';
        case 'GFS':
          return isSelected ? '#fbbf24' : '#d97706';
        default:
          return '#334155';
      }
    }

    if (activeLayer === 'trust') {
      const pct = sub.trust_percentage || 40;
      if (pct >= 55) return '#0369a1';
      if (pct >= 45) return '#0284c7';
      if (pct >= 35) return '#38bdf8';
      return '#7dd3fc';
    }

    if (activeLayer === 'disagreement') {
      if (sub.disagreement_level === 'HIGH') return 'url(#severeDisagreementHatch)';
      if (sub.disagreement_level === 'MEDIUM') return '#1e293b';
      return '#0f172a';
    }

    if (activeLayer === 'confidence') {
      if (sub.confidence === 'HIGH') return '#065f46';
      if (sub.confidence === 'MEDIUM') return '#92400e';
      return '#991b1b';
    }

    if (activeLayer === 'rainfall') {
      const rf = sub.rainfall_mm || 30;
      if (rf >= 80) return '#dc2626';
      if (rf >= 50) return '#0284c7';
      if (rf >= 25) return '#0d9488';
      return '#334155';
    }

    return '#1e293b';
  };

  return (
    <div className={`relative w-full ${heightClass} bg-surface-deep/95 rounded-xl border border-surface-border overflow-hidden flex flex-col select-none`}>
      {/* Top HUD Control Strip */}
      <div className="px-4 py-2.5 bg-surface/90 border-b border-surface-border flex flex-wrap items-center justify-between gap-2 z-20">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-primary" />
          <span className="font-headline font-bold text-xs text-on-surface tracking-wider uppercase">
            Geospatial Model Trust Map (India Met Grid)
          </span>
          <ProvenanceBadge type="PHYSICS_INFORMED_HEURISTIC" label="PHYSICS HEURISTIC" />
        </div>

        {/* Layer Switcher Buttons */}
        {showControls && (
          <div className="flex items-center gap-1 bg-surface-deep p-1 rounded-lg border border-surface-border">
            <button
              onClick={() => setActiveLayer('dominant')}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all ${
                activeLayer === 'dominant' ? 'bg-cyan-500 text-slate-950 font-bold shadow-xs' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Dominant Model
            </button>
            <button
              onClick={() => setActiveLayer('trust')}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all ${
                activeLayer === 'trust' ? 'bg-cyan-500 text-slate-950 font-bold shadow-xs' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Trust Intensity
            </button>
            <button
              onClick={() => setActiveLayer('disagreement')}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all ${
                activeLayer === 'disagreement' ? 'bg-cyan-500 text-slate-950 font-bold shadow-xs' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Disagreement
            </button>
            <button
              onClick={() => setActiveLayer('rainfall')}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all ${
                activeLayer === 'rainfall' ? 'bg-cyan-500 text-slate-950 font-bold shadow-xs' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Rainfall Isohyets
            </button>
          </div>
        )}
      </div>

      {/* SVG Met Canvas */}
      <div 
        className="dark relative flex-1 w-full bg-[#080e1c] flex items-center justify-center overflow-hidden"
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
        }}
      >
        <svg
          viewBox="0 0 950 900"
          className="w-full h-full max-h-[820px] select-none"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Severe Disagreement Hatch Pattern */}
            <pattern id="severeDisagreementHatch" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="10" stroke="#f59e0b" strokeWidth="2.5" strokeOpacity="0.9" />
              <rect width="10" height="10" fill="#451a03" fillOpacity="0.6" />
            </pattern>

            {/* Glowing Active Selection Filter */}
            <filter id="activeSubdivGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="8" floodColor="#00e5ff" floodOpacity="0.8" />
            </filter>

            {/* Isohyet radar gradient */}
            <radialGradient id="precipCore" cx="48%" cy="52%" r="40%">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.85" />
              <stop offset="35%" stopColor="#0284c7" stopOpacity="0.70" />
              <stop offset="70%" stopColor="#06b6d4" stopOpacity="0.30" />
              <stop offset="100%" stopColor="#080e1c" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Ocean Water Backdrop */}
          <rect width="950" height="900" fill="#060b17" />

          {/* Graticule Parallels */}
          <g stroke="#18253f" strokeWidth="0.8" strokeDasharray="3 4">
            <line x1="40" y1="130" x2="910" y2="130" />
            <line x1="40" y1="260" x2="910" y2="260" />
            <line x1="40" y1="390" x2="910" y2="390" />
            <line x1="40" y1="520" x2="910" y2="520" />
            <line x1="40" y1="650" x2="910" y2="650" />
            <line x1="40" y1="780" x2="910" y2="780" />
          </g>

          {/* Graticule Meridians */}
          <g stroke="#18253f" strokeWidth="0.8" strokeDasharray="3 4">
            <line x1="160" y1="40" x2="160" y2="860" />
            <line x1="290" y1="40" x2="290" y2="860" />
            <line x1="420" y1="40" x2="420" y2="860" />
            <line x1="550" y1="40" x2="550" y2="860" />
            <line x1="680" y1="40" x2="680" y2="860" />
            <line x1="810" y1="40" x2="810" y2="860" />
          </g>

          {/* Graticule Text Coordinates */}
          <g fill="#475569" className="font-mono text-[9px]">
            <text x="45" y="126">32° N</text>
            <text x="45" y="256">28° N</text>
            <text x="45" y="386">24° N</text>
            <text x="45" y="516">20° N</text>
            <text x="45" y="646">16° N</text>
            <text x="45" y="776">12° N</text>
            <text x="162" y="875">72° E</text>
            <text x="292" y="875">76° E</text>
            <text x="422" y="875">80° E</text>
            <text x="552" y="875">84° E</text>
            <text x="682" y="875">88° E</text>
            <text x="812" y="875">92° E</text>
          </g>

          {/* Maritime Basin Labels */}
          <text x="90" y="660" fill="#334155" className="font-mono text-[11px] font-bold tracking-widest uppercase">
            Arabian Sea
          </text>
          <text x="690" y="650" fill="#334155" className="font-mono text-[11px] font-bold tracking-widest uppercase">
            Bay of Bengal
          </text>
          <text x="360" y="870" fill="#334155" className="font-mono text-[10px] font-bold tracking-widest uppercase">
            Indian Ocean Basin
          </text>

          {/* 1. J&K / Ladakh */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[12])}
            onMouseEnter={() => setHoveredSub(subdivisions[12])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="310,50 365,65 385,100 370,145 320,150 280,115 285,75"
              fill={getSubColor(subdivisions[12])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[12].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[12].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="305" y="105" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">J&K / LADAKH</text>
            <text x="312" y="118" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[12])}</text>
          </g>

          {/* 2. Punjab & HP */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[13])}
            onMouseEnter={() => setHoveredSub(subdivisions[13])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="275,120 320,150 340,195 295,215 260,180 265,145"
              fill={getSubColor(subdivisions[13])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[13].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[13].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="272" y="170" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">PUNJAB & HP</text>
            <text x="280" y="182" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[13])}</text>
          </g>

          {/* 3. W. Rajasthan */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[8])}
            onMouseEnter={() => setHoveredSub(subdivisions[8])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="200,205 260,180 290,215 265,305 185,310 170,240"
              fill={getSubColor(subdivisions[8])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[8].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[8].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="200" y="250" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">W. RAJASTHAN</text>
            <text x="208" y="263" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[8])}</text>
          </g>

          {/* 4. Gujarat & Saurashtra */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[5])}
            onMouseEnter={() => setHoveredSub(subdivisions[5])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="120,345 190,320 225,355 240,410 195,435 140,410 115,370"
              fill={getSubColor(subdivisions[5])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[5].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[5].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="145" y="380" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">GUJARAT</text>
            <text x="148" y="393" fill="#c084fc" className="font-mono text-[9px] font-semibold pointer-events-none">{subLabel(subdivisions[5])}</text>
          </g>

          {/* 5. Vidarbha / Central */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[4])}
            onMouseEnter={() => setHoveredSub(subdivisions[4])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="265,305 380,270 450,305 450,400 370,425 285,415 240,360"
              fill={getSubColor(subdivisions[4])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[4].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[4].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="320" y="345" fill="#f1f5f9" className="font-headline text-[11px] font-bold pointer-events-none">VIDARBHA / MP</text>
            <text x="335" y="360" fill="#94a3b8" className="font-mono text-[9px] font-semibold pointer-events-none">{subLabel(subdivisions[4])}</text>
          </g>

          {/* 6. Gangetic Bengal */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[6])}
            onMouseEnter={() => setHoveredSub(subdivisions[6])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="380,270 550,250 595,290 560,380 470,360 450,305"
              fill={getSubColor(subdivisions[6])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[6].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[6].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="470" y="305" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">GANGETIC BENGAL</text>
            <text x="495" y="318" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[6])}</text>
          </g>

          {/* 7. Assam & Meghalaya */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[7])}
            onMouseEnter={() => setHoveredSub(subdivisions[7])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="620,240 730,210 780,250 740,320 670,310 635,270"
              fill={getSubColor(subdivisions[7])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[7].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[7].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="660" y="270" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">ASSAM / MEG</text>
            <text x="670" y="283" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[7])}</text>
          </g>

          {/* 8. Konkan & Goa / Mumbai */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[2])}
            onMouseEnter={() => setHoveredSub(subdivisions[2])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="225,435 305,420 360,455 330,555 255,540 220,490"
              fill={getSubColor(subdivisions[2])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[2].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[2].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="245" y="480" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">KONKAN & MH</text>
            <text x="248" y="494" fill="#6ee7b7" className="font-mono text-[8px] font-bold pointer-events-none">{subLabel(subdivisions[2])}</text>
          </g>

          {/* 9. Odisha Coast (Severe Disagreement Zone) */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[3])}
            onMouseEnter={() => setHoveredSub(subdivisions[3])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="460,390 560,375 600,430 545,510 470,480 445,435"
              fill={getSubColor(subdivisions[3])}
              stroke="#f59e0b"
              strokeWidth={regionId === subdivisions[3].id ? "3" : "1.8"}
              filter={regionId === subdivisions[3].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <circle cx="525" cy="445" r="4" fill="#f59e0b" />
            <circle cx="525" cy="445" r="3" fill="#d97706" />
            <text x="482" y="468" fill="#fef08a" className="font-headline text-[9px] font-bold pointer-events-none">ODISHA COAST</text>
            <text x="482" y="476" fill="#fca5a5" className="font-mono text-[8px] font-bold pointer-events-none">HIGH SPREAD</text>
          </g>

          {/* 10. ACTIVE FOCUS: TELANGANA MET SUBDIVISION (Zone 04) */}
          <g 
            className="cursor-pointer"
            onClick={() => handleSubClick(subdivisions[0])}
            onMouseEnter={() => setHoveredSub(subdivisions[0])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="345,475 440,450 475,520 420,605 345,565"
              fill={getSubColor(subdivisions[0])}
              stroke="#00e5ff"
              strokeWidth={regionId === subdivisions[0].id ? "3.5" : "2"}
              filter="url(#activeSubdivGlow)"
            />

            {/* Pulsing Doppler Station Reticle (Coords: ~17.8°N, 79.1°E) */}
            <g transform="translate(400, 530)">
              <circle cx="0" cy="0" r="18" fill="none" stroke="#00e5ff" strokeWidth="1.2" strokeDasharray="3 3" className="animate-spin-slow" />
              <circle cx="0" cy="0" r="10" fill="none" stroke="#38bdf8" strokeWidth="1.5" />
              <circle cx="0" cy="0" r="4" fill="#ffffff" />
              <circle cx="0" cy="0" r="2" fill="#00e5ff" />
              <line x1="-14" y1="0" x2="14" y2="0" stroke="#00e5ff" strokeWidth="1" />
              <line x1="0" y1="-14" x2="0" y2="14" stroke="#00e5ff" strokeWidth="1" />
            </g>

            {/* Nameplate Tag */}
            <rect x="350" y="555" width="130" height="32" rx="3" fill="#03162b" fillOpacity="0.94" stroke="#00e5ff" strokeWidth="1" />
            <text x="358" y="569" fill="#38bdf8" className="font-headline text-[10px] font-bold pointer-events-none">TELANGANA (ZONE 04)</text>
            <text x="358" y="581" fill="#ffffff" className="font-mono text-[9px] font-semibold pointer-events-none">NCUM DOMINANT: 46%</text>
          </g>

          {/* 11. Andhra & Rayalaseema */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[9])}
            onMouseEnter={() => setHoveredSub(subdivisions[9])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="420,605 475,520 545,510 500,670 435,665 395,620"
              fill={getSubColor(subdivisions[9])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[9].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[9].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="440" y="600" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">ANDHRA</text>
            <text x="450" y="612" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[9])}</text>
          </g>

          {/* 12. Karnataka */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[10])}
            onMouseEnter={() => setHoveredSub(subdivisions[10])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="275,550 345,565 395,620 375,700 295,670"
              fill={getSubColor(subdivisions[10])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[10].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[10].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="305" y="615" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">KARNATAKA</text>
            <text x="312" y="628" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[10])}</text>
          </g>

          {/* 13. Tamil Nadu */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[11])}
            onMouseEnter={() => setHoveredSub(subdivisions[11])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="375,700 440,665 435,770 365,820 345,770"
              fill={getSubColor(subdivisions[11])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[11].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[11].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="370" y="745" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">TAMIL NADU</text>
            <text x="372" y="758" fill="#94a3b8" className="font-mono text-[8px] pointer-events-none">{subLabel(subdivisions[11])}</text>
          </g>

          {/* 14. Kerala & Western Ghats */}
          <g 
            className="subdiv-polygon"
            onClick={() => handleSubClick(subdivisions[1])}
            onMouseEnter={() => setHoveredSub(subdivisions[1])}
            onMouseLeave={() => setHoveredSub(null)}
          >
            <polygon
              points="295,670 345,770 325,830 300,810 270,720"
              fill={getSubColor(subdivisions[1])}
              stroke="#1e293b"
              strokeWidth={regionId === subdivisions[1].id ? "2.5" : "1.2"}
              filter={regionId === subdivisions[1].id ? "url(#activeSubdivGlow)" : undefined}
            />
            <text x="260" y="770" fill="#f1f5f9" className="font-headline text-[10px] font-bold pointer-events-none">KERALA</text>
            <text x="250" y="783" fill="#6ee7b7" className="font-mono text-[8px] font-bold pointer-events-none">{subLabel(subdivisions[1])}</text>
          </g>

          {/* Convective Core Isohyets Overlay (When in rainfall layer) */}
          {activeLayer === 'rainfall' && (
            <g opacity="0.85">
              <ellipse cx="445" cy="520" rx="90" ry="70" fill="url(#precipCore)" />
              <circle cx="445" cy="520" r="35" fill="#ef4444" fillOpacity="0.4" />
              <text x="410" y="524" fill="#ffffff" className="font-mono text-[11px] font-bold">
                &gt; 75 mm/48h
              </text>
            </g>
          )}
        </svg>

        {/* Hover Tooltip Card */}
        {hoveredSub && (
          <div
            className="absolute z-30 pointer-events-none p-3 rounded-lg bg-surface-deep/95 border border-cyan-500/50 shadow-xl backdrop-blur-md text-on-surface min-w-[210px]"
            style={{
              left: `${Math.min(mousePos.x + 15, 650)}px`,
              top: `${Math.min(mousePos.y + 15, 450)}px`
            }}
          >
            <div className="font-headline font-bold text-sm text-primary">{hoveredSub.name}</div>
            <div className="text-[10px] font-mono text-on-surface-variant mt-0.5">{hoveredSub.terrain}</div>
            
            <div className="mt-2 space-y-1 text-xs font-mono border-t border-surface-border pt-1.5">
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Dominant Model:</span>
                <span className="font-bold text-on-surface">{hoveredSub.dominant_model}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Assigned Trust:</span>
                <span className="font-bold text-primary">{hoveredSub.trust_percentage}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Rainfall:</span>
                <span className="font-bold text-on-surface">{hoveredSub.rainfall_mm} mm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Disagreement:</span>
                <span className={`font-bold ${hoveredSub.disagreement_level === 'HIGH' ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                  {hoveredSub.disagreement_level}
                </span>
              </div>
            </div>

            <div className="mt-2 text-[9px] font-mono text-primary/80">Click to open Regional Deep-Dive →</div>
          </div>
        )}

        {/* Floating Map Legend Bar */}
        <div className="absolute bottom-3 left-3 z-20 bg-surface/90 backdrop-blur-md p-2 rounded-lg border border-surface-border shadow-md">
          <div className="text-[10px] font-mono text-on-surface-variant uppercase tracking-wider mb-1 font-semibold">
            {activeLayer === 'dominant' ? 'Model Legend' : activeLayer === 'disagreement' ? 'Disagreement Legend' : 'Map Legend'}
          </div>
          <div className="flex items-center gap-3 text-xs font-mono">
            {activeLayer === 'dominant' ? (
              <>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-[#0284c7]" />
                  <span className="text-on-surface-variant">NCUM (Synoptic)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-[#059669]" />
                  <span className="text-on-surface-variant">WRF (Orography)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-[#6366f1]" />
                  <span className="text-on-surface-variant">AI Weather (Meta)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-[#d97706]" />
                  <span className="text-on-surface-variant">GFS (Global)</span>
                </div>
              </>
            ) : activeLayer === 'disagreement' ? (
              <>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-amber-500" />
                  <span className="text-on-surface-variant">High Spread (Crosshatch)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-sm bg-surface-container-highest" />
                  <span className="text-on-surface-variant">Consensus Achieved</span>
                </div>
              </>
            ) : (
              <div className="text-[11px] text-on-surface-variant">
                Layer: <strong className="text-primary uppercase">{activeLayer}</strong> (14 Met Subdivisions)
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
