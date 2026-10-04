import React from 'react';
import { useVaruna } from '../../context/VarunaContext';
import {
  Monitor,
  CloudRain,
  Share2,
  Map,
  Compass,
  AlertTriangle,
  HelpCircle,
  Clock,
  CheckCircle2,
  BarChart3,
  BrainCircuit,
  Activity,
  FileCheck,
  Server,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  Radio,
  Database,
  Users,
  ShieldCheck
} from 'lucide-react';
import { UserRole } from '../../types';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  roles: UserRole[];
}

interface NavGroup {
  name: string;
  items: NavItem[];
}

export const Sidebar: React.FC = () => {
  const {
    activeRoute, setActiveRoute, role, isControlRoomFullscreen,
    isSidebarCollapsed: collapsed, setIsSidebarCollapsed: setCollapsed,
    isMobileNavOpen, setIsMobileNavOpen, summary, dataSourceStatus
  } = useVaruna();

  if (isControlRoomFullscreen) return null;

  const ALL: UserRole[] = ['FORECASTER', 'OPERATIONS', 'MODEL_ANALYST', 'ADMIN', 'AUDITOR'];
  const navGroups: NavGroup[] = [
    {
      name: "FORECAST",
      items: [
        { id: 'control-room', label: 'Control Room', icon: <Monitor className="w-4 h-4" />, roles: ALL },
        { id: 'forecast', label: 'Forecast Intelligence', icon: <CloudRain className="w-4 h-4" />, roles: ALL },
        { id: 'fusion', label: 'Fusion Centre', icon: <Share2 className="w-4 h-4" />, roles: ALL },
        { id: 'trust-map', label: 'Model Trust Map', icon: <Map className="w-4 h-4" />, roles: ALL },
        { id: 'regional', label: 'Regional Deep-Dive', icon: <Compass className="w-4 h-4" />, roles: ALL },
        { id: 'extremes', label: 'Extreme Events', icon: <AlertTriangle className="w-4 h-4 text-error" />, badge: summary?.extreme_guidance?.is_extreme ? '!' : undefined, roles: ALL }
      ]
    },
    {
      name: "EXPLAIN & VERIFY",
      items: [
        { id: 'why-this-forecast', label: 'Why This Forecast?', icon: <HelpCircle className="w-4 h-4" />, roles: ['FORECASTER', 'MODEL_ANALYST', 'ADMIN', 'AUDITOR'] },
        { id: 'what-changed', label: 'What Changed?', icon: <Clock className="w-4 h-4" />, roles: ['FORECASTER', 'MODEL_ANALYST', 'ADMIN', 'AUDITOR'] },
        { id: 'verification', label: 'Verification Centre', icon: <CheckCircle2 className="w-4 h-4 text-secondary" />, roles: ALL },
        { id: 'model-performance', label: 'Model Performance & Skill', icon: <BarChart3 className="w-4 h-4" />, roles: ['MODEL_ANALYST', 'ADMIN', 'AUDITOR'] },
        { id: 'failure-memory', label: 'Model Failure & Drift', icon: <BrainCircuit className="w-4 h-4" />, roles: ['FORECASTER', 'MODEL_ANALYST', 'ADMIN'] },
        { id: 'experiments', label: 'Experiments', icon: <FlaskConical className="w-4 h-4" />, roles: ['MODEL_ANALYST', 'ADMIN'] }
      ]
    },
    {
      name: "DATA & OPERATIONS",
      items: [
        { id: 'live-data', label: 'Data Sources (India-first)', icon: <Radio className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />, roles: ALL },
        { id: 'operations', label: 'Source Health & Dropout', icon: <Activity className="w-4 h-4" />, roles: ['OPERATIONS', 'ADMIN'] },
        { id: 'data-health', label: 'Data Health', icon: <Database className="w-4 h-4" />, roles: ['OPERATIONS', 'MODEL_ANALYST', 'ADMIN'] },
        { id: 'system-health', label: 'System Health', icon: <Server className="w-4 h-4" />, roles: ['ADMIN', 'OPERATIONS'] }
      ]
    },
    {
      name: "GOVERNANCE",
      items: [
        { id: 'governance', label: 'Governance & Users', icon: <Users className="w-4 h-4" />, roles: ['MODEL_ANALYST', 'ADMIN', 'AUDITOR'] },
        { id: 'audit', label: 'Audit Trail', icon: <ShieldCheck className="w-4 h-4" />, roles: ['ADMIN', 'AUDITOR'] },
        { id: 'provenance', label: 'Data Provenance', icon: <FileCheck className="w-4 h-4" />, roles: ['MODEL_ANALYST', 'ADMIN', 'AUDITOR'] }
      ]
    }
  ];

  return (
    <>
    {/* Mobile backdrop */}
    {isMobileNavOpen && (
      <div className="fixed inset-0 top-14 z-30 bg-black/40 lg:hidden" onClick={() => setIsMobileNavOpen(false)} />
    )}
    <aside
      className={`fixed left-0 top-14 bottom-0 z-40 bg-surface-container-lowest border-r border-outline-variant/30 transition-all duration-300 flex-col justify-between overflow-y-auto ${
        isMobileNavOpen ? 'flex w-72' : 'hidden lg:flex'
      } ${collapsed && !isMobileNavOpen ? 'lg:w-16' : 'lg:w-72'}`}
    >
      <div className="p-3">
        {navGroups.map((grp) => {
          const visibleItems = grp.items.filter(item => item.roles.includes(role));
          if (visibleItems.length === 0) return null;

          return (
            <div key={grp.name} className="mb-4">
              {!collapsed && (
                <div className="px-2 mb-1.5 font-mono text-[10px] text-outline uppercase tracking-wider font-bold">
                  {grp.name}
                </div>
              )}

              <nav className="flex flex-col gap-0.5">
                {visibleItems.map((item) => {
                  const isActive = activeRoute === item.id;

                  return (
                    <button
                      key={item.id}
                      onClick={() => { setActiveRoute(item.id); setIsMobileNavOpen(false); }}
                      aria-current={isActive ? 'page' : undefined}
                      className={`flex items-center justify-between px-2.5 py-2 rounded-lg transition-colors text-xs text-left w-full ${
                        isActive
                          ? 'bg-primary-container text-on-primary-container font-semibold shadow-xs'
                          : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface font-medium'
                      }`}
                      title={collapsed ? item.label : undefined}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span className={`shrink-0 ${isActive ? 'text-on-primary-container' : 'text-on-surface-variant'}`}>
                          {item.icon}
                        </span>
                        {!collapsed && (
                          <span className="truncate">{item.label}</span>
                        )}
                      </div>

                      {!collapsed && item.badge && (
                        <span className="px-1.5 py-0.2 rounded-full bg-error-container text-on-error-container font-mono text-[10px] font-bold">
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>
            </div>
          );
        })}
      </div>

      {/* Bottom Diagnostics / Telemetry Box */}
      <div className="p-3">
        {!collapsed ? (
          <div className="p-3 bg-surface-container-low/70 rounded-lg border border-outline-variant/20 flex flex-col gap-1.5 font-mono text-xs">
            {/* Real session status (replaces hard-coded "100% / 0 Pkts / 42ms" telemetry) */}
            <div className="flex items-center justify-between">
              <span className="text-on-surface-variant">Backend</span>
              <span className={`font-bold ${dataSourceStatus?.backendConnected ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                {dataSourceStatus?.backendConnected ? 'LIVE' : 'OFFLINE DEMO'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-on-surface-variant">Data</span>
              <span className="text-on-surface font-semibold">{summary?.source_mode?.startsWith('INDIA') ? 'NCMRWF/IMD' : summary?.source_mode === 'LIVE_PUBLIC_MODELS' ? 'GLOBAL MODELS' : summary?.source_mode === 'STORED_DATA' ? 'STORED' : 'SYNTHETIC'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-on-surface-variant">Active feeds</span>
              <span className="text-on-surface font-semibold">
                {(summary?.weights || []).filter(w => w.weight > 0).length}/{(summary?.weights || []).length || 4}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-on-surface-variant">Last refresh</span>
              <span className="text-secondary font-semibold">
                {dataSourceStatus?.lastUpdated ? new Date(dataSourceStatus.lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
              </span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center p-2" title={dataSourceStatus?.backendConnected ? 'Backend connected' : 'Offline demo'}>
            <span className={`w-2 h-2 rounded-full ${dataSourceStatus?.backendConnected ? 'bg-emerald-500' : 'bg-amber-500'}`} />
          </div>
        )}

        <div className="mt-2 pt-2 border-t border-outline-variant/20 flex items-center justify-between px-1">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex p-1 rounded hover:bg-surface-container-high text-on-surface-variant text-xs flex items-center gap-1 font-mono"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <><ChevronLeft className="w-4 h-4" /> <span>Collapse</span></>}
          </button>
          {!collapsed && (
            <span className="font-mono text-[9px] text-outline">v1.0 · prototype</span>
          )}
        </div>
      </div>
    </aside>
    </>
  );
};
