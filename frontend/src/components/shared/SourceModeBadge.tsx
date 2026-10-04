import React from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { fmtTime } from '../../utils/models';

/** One honest label for where the numbers on screen came from. */
export const useSourceMode = () => {
  const { summary, dataMode } = useVaruna();
  if (dataMode === 'DEMO') return { key: 'OFFLINE', label: 'Offline demo · synthetic', tone: 'amber', detail: 'Backend unreachable: local synthetic fixtures.' };
  switch (summary.source_mode) {
    case 'INDIA_OPERATIONAL':
      return { key: 'INDIA', label: 'NCMRWF / IMD feeds', tone: 'emerald',
               detail: `Authorised Indian forecast files (NCMRWF / IMD), latest issue ${fmtTime(summary.issue_time)}.` };
    case 'INDIA_OPERATIONAL_PLUS_GLOBAL':
      return { key: 'INDIA+', label: 'NCMRWF/IMD + global models', tone: 'emerald',
               detail: `Authorised Indian feeds merged with global public models for the same valid day (Indian copy preferred per model). Latest issue ${fmtTime(summary.issue_time)}.` };
    case 'LIVE_PUBLIC_MODELS':
      return { key: 'LIVE', label: 'Global public models', tone: 'sky',
               detail: `Open-Meteo model forecasts issued ${fmtTime(summary.issue_time)} (GFS / ECMWF / AIFS / UM / ICON) over India — reference lane. Add NCMRWF/IMD feeds in Data sources.` };
    case 'STORED_DATA':
      return { key: 'STORED', label: 'Stored data', tone: 'sky', detail: `Latest stored issue ${fmtTime(summary.issue_time)} from ${(summary.dataset_ids || []).join(', ') || 'uploaded datasets'}.` };
    default:
      return { key: 'DEMO', label: 'Synthetic demo scenario', tone: 'amber',
               detail: summary.source_note || 'Model values are a synthetic scenario. Add NCMRWF/IMD feeds or fetch global models in Data sources.' };
  }
};

const TONE: Record<string, string> = {
  emerald: 'bg-emerald-50 dark:bg-emerald-950/50 border-emerald-500/40 text-emerald-700 dark:text-emerald-300',
  amber: 'bg-amber-50 dark:bg-amber-950/50 border-amber-500/40 text-amber-800 dark:text-amber-300',
  sky: 'bg-sky-50 dark:bg-sky-950/50 border-sky-500/40 text-sky-700 dark:text-sky-300',
};

export const SourceModeBadge: React.FC<{ compact?: boolean; className?: string }> = ({ compact = false, className = '' }) => {
  const m = useSourceMode();
  return (
    <span title={m.detail} className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border font-mono text-[10px] font-bold uppercase whitespace-nowrap ${TONE[m.tone]} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.tone === 'emerald' ? 'bg-emerald-500' : m.tone === 'sky' ? 'bg-sky-500' : 'bg-amber-500'}`} />
      {compact ? m.key : m.label}
    </span>
  );
};
