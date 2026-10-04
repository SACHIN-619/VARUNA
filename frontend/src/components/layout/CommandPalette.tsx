import React, { useState } from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { 
  Search, 
  X, 
  Map, 
  CloudRain, 
  Share2, 
  CheckCircle2, 
  AlertTriangle, 
  Database, 
  Play, 
  Activity, 
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

interface CommandItem {
  id: string;
  title: string;
  category: string;
  icon: React.ReactNode;
  action: () => void;
}

export const CommandPalette: React.FC = () => {
  const { 
    isCommandPaletteOpen, 
    setIsCommandPaletteOpen, 
    setActiveRoute, 
    setIsDemoModalOpen,
    setIsFailureModalOpen,
    setRegionId,
    subdivisions
  } = useVaruna();

  const [query, setQuery] = useState<string>('');

  if (!isCommandPaletteOpen) return null;

  const commands: CommandItem[] = [
    {
      id: 'cmd-control-room',
      title: 'Enter Control Room (Command Centre HUD)',
      category: 'Command',
      icon: <CloudRain className="w-4 h-4 text-primary" />,
      action: () => { setActiveRoute('control-room'); setIsCommandPaletteOpen(false); }
    },
    {
      id: 'cmd-trust-map',
      title: 'Open Geospatial Model Trust Map',
      category: 'Geospatial',
      icon: <Map className="w-4 h-4 text-primary" />,
      action: () => { setActiveRoute('trust-map'); setIsCommandPaletteOpen(false); }
    },
    {
      id: 'cmd-fusion-centre',
      title: 'Open Fusion Centre & Mathematical Pipeline',
      category: 'Intelligence',
      icon: <Share2 className="w-4 h-4 text-primary" />,
      action: () => { setActiveRoute('fusion'); setIsCommandPaletteOpen(false); }
    },
    {
      id: 'cmd-verification',
      title: 'Open Verification Centre & MAE Skill Benchmarks',
      category: 'Verification',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />,
      action: () => { setActiveRoute('verification'); setIsCommandPaletteOpen(false); }
    },
    {
      id: 'cmd-extremes',
      title: 'Inspect Active Extreme Weather Matrix',
      category: 'Alerts',
      icon: <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400" />,
      action: () => { setActiveRoute('extremes'); setIsCommandPaletteOpen(false); }
    },
    {
      id: 'cmd-failure-sim',
      title: 'Launch Operational Failure & Dropout Simulator',
      category: 'Operations',
      icon: <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400" />,
      action: () => { setIsFailureModalOpen(true); setIsCommandPaletteOpen(false); }
    },
    {
      id: 'cmd-demo',
      title: 'Start VARUNA 10-Step Interactive Presentation Demo',
      category: 'Demonstration',
      icon: <Play className="w-4 h-4 text-primary" />,
      action: () => { setIsDemoModalOpen(true); setIsCommandPaletteOpen(false); }
    },
    {
      id: 'cmd-data-health',
      title: 'Inspect Ingestion Pipeline & Quality Control',
      category: 'Data Health',
      icon: <Database className="w-4 h-4 text-teal-700 dark:text-teal-400" />,
      action: () => { setActiveRoute('data-health'); setIsCommandPaletteOpen(false); }
    },
    // Region quick jumps
    ...subdivisions.map(s => ({
      id: `region-${s.id}`,
      title: `Jump to Region: ${s.name} (${s.state})`,
      category: 'Regions',
      icon: <Map className="w-4 h-4 text-on-surface-variant" />,
      action: () => {
        setRegionId(s.id);
        setActiveRoute('regional');
        setIsCommandPaletteOpen(false);
      }
    }))
  ];

  const filteredCommands = commands.filter(c => 
    c.title.toLowerCase().includes(query.toLowerCase()) || 
    c.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/60 backdrop-blur-xs p-4 animate-fadeIn">
      <div className="w-full max-w-xl bg-surface-container-lowest border border-outline-variant/30 rounded-xl shadow-2xl overflow-hidden flex flex-col">
        {/* Search Input Bar */}
        <div className="p-3.5 border-b border-outline-variant/30 flex items-center gap-3 bg-surface-container-low">
          <Search className="w-5 h-5 text-primary shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command, subdivision, model, or action... (e.g. Telangana, Trust Map, Demo)"
            className="w-full bg-transparent text-on-surface placeholder-on-surface-variant/60 text-sm font-mono focus:outline-none"
            autoFocus
          />
          <button
            onClick={() => setIsCommandPaletteOpen(false)}
            className="p-1 rounded text-on-surface-variant hover:text-on-surface"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Command List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {filteredCommands.length > 0 ? (
            filteredCommands.map((cmd) => (
              <button
                key={cmd.id}
                onClick={cmd.action}
                className="w-full text-left p-2.5 rounded-lg hover:bg-surface-container-high flex items-center justify-between text-xs font-mono text-on-surface transition-colors group"
              >
                <div className="flex items-center gap-2.5">
                  <span className="p-1.5 rounded bg-surface-container border border-outline-variant/30 text-on-surface-variant group-hover:text-primary">
                    {cmd.icon}
                  </span>
                  <div>
                    <div className="font-semibold text-on-surface">{cmd.title}</div>
                    <div className="text-[10px] text-on-surface-variant">{cmd.category}</div>
                  </div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-on-surface-variant/40 group-hover:text-primary transition-colors" />
              </button>
            ))
          ) : (
            <div className="p-6 text-center text-xs font-mono text-on-surface-variant">
              No matching meteorological commands found for "{query}".
            </div>
          )}
        </div>

        {/* Footer tip */}
        <div className="px-4 py-2 border-t border-outline-variant/30 bg-surface-container-low flex items-center justify-between text-[10px] font-mono text-on-surface-variant">
          <span>Tip: Press <kbd className="px-1 py-0.5 rounded bg-surface-container border border-outline-variant/30 text-on-surface">ESC</kbd> to dismiss</span>
          <span>VARUNA Operational Command Shell</span>
        </div>
      </div>
    </div>
  );
};
