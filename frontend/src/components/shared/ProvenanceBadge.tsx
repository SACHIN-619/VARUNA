import React from 'react';
import { ShieldAlert, CheckCircle2, Lock, Cpu, Sparkles, Info, Database, HelpCircle, Activity } from 'lucide-react';
import { ProvenanceType } from '../../types';

interface ProvenanceBadgeProps {
  type?: ProvenanceType | string;
  label?: string;
  showIcon?: boolean;
  className?: string;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({ 
  type = 'CONTROLLED_SYNTHETIC_BENCHMARK', 
  label, 
  showIcon = true,
  className = ''
}) => {
  const normType = (type || 'CONTROLLED_SYNTHETIC_BENCHMARK').toUpperCase().replace(/ /g, '_');

  const getBadgeConfig = () => {
    switch (normType) {
      case 'LIVE_CONNECTED':
        return {
          text: label || 'LIVE CONNECTED',
          bg: 'bg-emerald-50 dark:bg-emerald-950/80 border-emerald-500/50 text-emerald-600 dark:text-emerald-400',
          icon: <Activity className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />,
          tooltip: 'Active connection to live forecast pipeline.'
        };
      case 'DATABASE_VERIFIED':
        return {
          text: label || 'DATABASE VERIFIED',
          bg: 'bg-emerald-50 dark:bg-emerald-950/70 border-emerald-600/40 text-emerald-600 dark:text-emerald-400',
          icon: <Database className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />,
          tooltip: 'Historical evidence verified against database observations for exact region/lead/regime context.'
        };
      case 'PUBLIC_SOURCE':
        return {
          text: label || 'PUBLIC DATA SOURCE',
          bg: 'bg-blue-50 dark:bg-blue-950/70 border-blue-600/40 text-blue-700 dark:text-blue-300',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-blue-700 dark:text-blue-400" />,
          tooltip: 'Ingested from verified public meteorological data archive.'
        };
      case 'AUTHORIZED_PROVIDER':
      case 'AUTHORIZED_ACCESS_REQUIRED':
        return {
          text: label || 'AUTHORIZED PROVIDER',
          bg: 'bg-purple-50 dark:bg-purple-950/70 border-purple-600/40 text-purple-600 dark:text-purple-400',
          icon: <Lock className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />,
          tooltip: 'Institutional gateway integration active. Subject to provider access constraints.'
        };
      case 'SYNTHETIC_STRESS_TEST':
      case 'CONTROLLED_SYNTHETIC_BENCHMARK':
      case 'CONTROLLED_BENCHMARK':
      case 'SYNTHETIC_DEMO':
      case 'SYNTHETIC':
        return {
          text: label || 'CONTROLLED SYNTHETIC STRESS TEST',
          bg: 'bg-amber-50 dark:bg-amber-950/70 border-amber-600/40 text-amber-600 dark:text-amber-400',
          icon: <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />,
          tooltip: 'Controlled synthetic chronological stress benchmark (5,124 records). Not operational meteorological data.'
        };
      case 'BOOTSTRAP_PRIOR':
        return {
          text: label || 'BOOTSTRAP PRIOR (COLD START)',
          bg: 'bg-indigo-50 dark:bg-indigo-950/70 border-indigo-600/40 text-indigo-600 dark:text-indigo-400',
          icon: <HelpCircle className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />,
          tooltip: 'Cold-start prior allocated (n=0 sample count). No matching historical verification evidence available.'
        };
      case 'NOT_VERIFIED':
        return {
          text: label || 'NOT VERIFIED',
          bg: 'bg-surface-container-high/90 border-outline-variant/60 text-on-surface-variant',
          icon: <ShieldAlert className="w-3.5 h-3.5 text-on-surface-variant" />,
          tooltip: 'No verification observation currently available for this forecast valid time.'
        };
      case 'UNAVAILABLE':
        return {
          text: label || 'UNAVAILABLE',
          bg: 'bg-rose-50 dark:bg-rose-950/70 border-rose-600/40 text-rose-600 dark:text-rose-400',
          icon: <ShieldAlert className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />,
          tooltip: 'Source or evidence unavailable for current query context.'
        };
      case 'PHYSICS_INFORMED_HEURISTIC':
        return {
          text: label || 'PHYSICS-INFORMED HEURISTIC',
          bg: 'bg-sky-50 dark:bg-sky-950/70 border-sky-600/40 text-primary',
          icon: <Cpu className="w-3.5 h-3.5 text-primary" />,
          tooltip: 'Derived from Indian terrain orography, Western Ghats escarpments, and monsoon trough physics.'
        };
      case 'ENGINEERING_FIXTURE':
        return {
          text: label || 'ENGINEERING FIXTURE',
          bg: 'bg-surface-container border-outline-variant text-on-surface-variant',
          icon: <Info className="w-3.5 h-3.5 text-on-surface-variant" />,
          tooltip: 'Controlled reproducible test fixture for CI validation and integration benchmarking.'
        };
      default:
        return {
          text: label || normType.replace(/_/g, ' '),
          bg: 'bg-surface-container-high/80 border-outline-variant/40 text-on-surface-variant',
          icon: <ShieldAlert className="w-3.5 h-3.5 text-on-surface-variant" />,
          tooltip: 'Scientific provenance explicitly tagged.'
        };
    }
  };

  const config = getBadgeConfig();

  return (
    <span 
      title={config.tooltip}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium tracking-wide border shadow-xs select-none ${config.bg} ${className}`}
    >
      {showIcon && config.icon}
      <span>{config.text}</span>
    </span>
  );
};

