import React from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { DataSourcePref, LeadHours, VariableType, WeatherRegime } from '../../types';
import { SourceModeBadge } from '../shared/SourceModeBadge';

const sel = 'appearance-none bg-surface-container-low border border-outline-variant/40 text-on-surface text-xs rounded px-2 py-1 pr-5 cursor-pointer hover:border-primary focus:outline-none focus:ring-1 focus:ring-primary min-w-0 max-w-full';

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <label className="flex items-center gap-1 min-w-0">
    <span className="text-[10px] uppercase tracking-wide text-on-surface-variant shrink-0">{label}</span>
    {children}
  </label>
);

/**
 * Forecast context (region, variable, lead, regime, data source). Lives under the navbar and wraps
 * onto extra lines instead of disappearing at narrow widths or high zoom.
 */
export const ContextBar: React.FC = () => {
  const {
    regionId, setRegionId, variable, setVariable, leadHours, setLeadHours, weatherRegime, setWeatherRegime,
    subdivisions, dataSourcePref, setDataSourcePref, isLoading,
  } = useVaruna();
  return (
    <div className="md:sticky md:top-14 z-30 bg-surface-container-lowest/95 backdrop-blur border-b border-outline-variant/30 px-4 lg:px-6 py-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 font-mono">
      <Field label="Region">
        <select value={regionId} onChange={e => setRegionId(e.target.value)} className={`${sel} max-w-[220px]`}>
          {subdivisions.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </Field>
      <Field label="Variable">
        <select value={variable} onChange={e => setVariable(e.target.value as VariableType)} className={sel}>
          <option value="rainfall">Rainfall (mm/24 h)</option>
          <option value="temperature">Max temp (°C)</option>
          <option value="wind_speed">Max wind (m/s)</option>
        </select>
      </Field>
      <Field label="Lead">
        <select value={leadHours} onChange={e => setLeadHours(Number(e.target.value) as LeadHours)} className={sel}>
          <option value={24}>+24 h</option><option value={48}>+48 h</option><option value={72}>+72 h</option>
        </select>
      </Field>
      <Field label="Regime">
        <select value={weatherRegime} onChange={e => setWeatherRegime(e.target.value as WeatherRegime)} className={sel} title="Selected by the forecaster; not auto-detected in this prototype">
          <option value="NORMAL">Normal</option>
          <option value="HEAVY_RAINFALL">Heavy rainfall</option>
          <option value="CONVECTIVE">Convective</option>
          <option value="TRANSITION_UNCERTAIN">Transition</option>
        </select>
      </Field>
      <Field label="Data">
        <select value={dataSourcePref} onChange={e => setDataSourcePref(e.target.value as DataSourcePref)} className={sel}
          title="auto = freshest NCMRWF/IMD files plus global public models (last 36 h); otherwise the synthetic demo">
          <option value="auto">Auto (India-first)</option>
          <option value="live">Global public models only</option>
          <option value="database">Stored / uploaded</option>
          <option value="demo">Synthetic demo</option>
        </select>
      </Field>
      <div className="hidden sm:flex items-center gap-2 ml-auto">
        {isLoading && <span className="text-[10px] text-on-surface-variant">updating…</span>}
        <SourceModeBadge />
      </div>
    </div>
  );
};
