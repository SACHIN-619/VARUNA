import React from 'react';
import { useVaruna } from '../context/VarunaContext';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { Settings, Sliders, Moon, ShieldCheck, Database, RotateCcw } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { regionId, setRegionId, variable, setVariable, leadHours, setLeadHours, weatherRegime, setWeatherRegime, subdivisions, theme, toggleTheme } = useVaruna();

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn max-w-4xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider">
              System Configuration
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="OPERATIONAL CONFIG" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            PLATFORM SETTINGS
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Configure default meteorological horizons, operational roles, and presentation mode parameters.
          </p>
        </div>
      </div>

      {/* Settings Sections */}
      <div className="space-y-5 font-mono text-xs">
        {/* Forecast Defaults */}
        <div className="p-5 rounded-2xl bg-surface border border-surface-border space-y-4">
          <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider flex items-center gap-2">
            <Sliders className="w-4 h-4 text-primary" />
            <span>Meteorological Defaults</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-on-surface-variant block mb-1">Default Meteorological Subdivision:</label>
              <select
                value={regionId}
                onChange={(e) => setRegionId(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-surface-deep border border-surface-border text-on-surface"
              >
                {subdivisions.map(s => (
                  <option key={s.id} value={s.id}>{s.name} ({s.state})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-on-surface-variant block mb-1">Default Weather Regime:</label>
              <select
                value={weatherRegime}
                onChange={(e) => setWeatherRegime(e.target.value as any)}
                className="w-full p-2.5 rounded-lg bg-surface-deep border border-surface-border text-on-surface"
              >
                <option value="NORMAL">Normal</option>
                <option value="HEAVY_RAINFALL">Heavy Rainfall</option>
                <option value="CONVECTIVE">Convective</option>
                <option value="TRANSITION_UNCERTAIN">Transition / Uncertain</option>
              </select>
            </div>
          </div>
        </div>

        {/* Appearance */}
        <div className="p-5 rounded-2xl bg-surface border border-surface-border space-y-3">
          <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider flex items-center gap-2">
            <Moon className="w-4 h-4 text-primary" />
            <span>Theme & Display Engine</span>
          </h3>
          <p className="text-on-surface-variant font-sans text-xs">
            Dark theme is tuned for 24/7 control rooms; light theme for daylight offices and printing. Your choice is remembered on this device (default follows the OS setting).
          </p>
          <button
            onClick={toggleTheme}
            className="w-full p-3 rounded-lg bg-surface-deep border border-surface-border text-on-surface flex items-center justify-between hover:border-primary transition-colors"
          >
            <span>{theme === 'dark' ? 'Dark theme' : 'Light theme'}</span>
            <span className="text-primary font-bold">Switch to {theme === 'dark' ? 'light' : 'dark'} →</span>
          </button>
        </div>
      </div>
    </div>
  );
};
