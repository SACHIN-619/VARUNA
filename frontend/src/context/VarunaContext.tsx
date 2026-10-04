import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { 
  UserRole, 
  VariableType, 
  LeadHours, 
  WeatherRegime, 
  DashboardSummary, 
  IndianSubdivision, 
  ModelId,
  ModelWeight,
  DataMode,
  DataSourceStatus,
  ForecastIntelligencePackage,
  DataSourcePref
} from '../types';
import { 
  fetchDashboardSummary, 
  fetchForecastPackage,
  getFallbackDashboard, 
  fallbackSubdivisions 
} from '../services/api';
import { AuthUser, getStoredUser, logoutUser, hasPermission } from '../services/auth';
import { listNotifications, VarunaNotification } from '../services/platform';

interface VarunaContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  regionId: string;
  setRegionId: (id: string) => void;
  variable: VariableType;
  setVariable: (v: VariableType) => void;
  leadHours: LeadHours;
  setLeadHours: (h: LeadHours) => void;
  weatherRegime: WeatherRegime;
  setWeatherRegime: (r: WeatherRegime) => void;
  summary: DashboardSummary;
  subdivisions: IndianSubdivision[];
  isLoading: boolean;
  refreshData: () => Promise<void>;
  
  // Data mode & provenance status
  dataMode: DataMode;
  dataSourceStatus: DataSourceStatus;
  forecastPackage: ForecastIntelligencePackage | null;

  // Navigation & View State
  activeRoute: string;
  setActiveRoute: (route: string) => void;
  
  // Interactive Drawers & Overlays
  activeTraceModel: ModelId | null;
  setActiveTraceModel: (m: ModelId | null) => void;
  selectedSubdivision: IndianSubdivision | null;
  setSelectedSubdivision: (s: IndianSubdivision | null) => void;
  isFailureModalOpen: boolean;
  setIsFailureModalOpen: (open: boolean) => void;
  isDemoModalOpen: boolean;
  setIsDemoModalOpen: (open: boolean) => void;
  isCommandPaletteOpen: boolean;
  setIsCommandPaletteOpen: (open: boolean) => void;
  isControlRoomFullscreen: boolean;
  setIsControlRoomFullscreen: (fs: boolean) => void;
  isUploadModalOpen: boolean;
  setIsUploadModalOpen: (open: boolean) => void;
  
  // Dropout demo simulation state
  simulatedDisabledModel: ModelId | null;
  setSimulatedDisabledModel: (m: ModelId | null) => void;
  simulateModelDropout: (m?: ModelId) => void;
  resetFailureState: () => void;
  isModelDropoutActive: boolean;
  weights: ModelWeight[];
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  maxRole: UserRole;
  isSidebarCollapsed: boolean;
  setIsSidebarCollapsed: (c: boolean) => void;
  isMobileNavOpen: boolean;
  setIsMobileNavOpen: (o: boolean) => void;
  authUser: AuthUser | null;
  logout: () => void;
  benchmark: BenchmarkSummary | null;
  /** Permission check against the signed-in user's backend role matrix. */
  can: (permission: string) => boolean;
  dataSourcePref: DataSourcePref;
  setDataSourcePref: (p: DataSourcePref) => void;
  notifications: VarunaNotification[];
  unreadCount: number;
  refreshNotifications: () => Promise<void>;
}

export interface BenchmarkSummary {
  ml_pct: number;
  stacking_pct?: number | null;
  best_method?: string;
  test_days?: number;
}

/** Formats the measured benchmark gain, e.g. "+1.0% ML · +2.9% stacking" (never a hard-coded number). */
export const formatBenchmark = (b: BenchmarkSummary | null): string => {
  if (!b) return 'benchmark: see Verification Centre';
  const f = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`;
  return `${f(b.ml_pct)} ML${b.stacking_pct != null ? ` · ${f(b.stacking_pct)} stacking` : ''} vs avg (synthetic)`;
};

const VarunaContext = createContext<VarunaContextType | undefined>(undefined);

// Backend roles are FORECASTER | OPERATIONS | ANALYST | ADMIN; the UI uses MODEL_ANALYST.
// Without this mapping an ANALYST login matched no sidebar entry and saw an empty menu.
export const normalizeRole = (r?: string | null): UserRole => {
  const up = (r || '').toUpperCase();
  if (up === 'ANALYST' || up === 'MODEL_ANALYST') return 'MODEL_ANALYST';
  if (up === 'OPERATIONS' || up === 'ADMIN' || up === 'FORECASTER' || up === 'AUDITOR') return up as UserRole;
  return 'FORECASTER';
};

// Privilege order for "view as": a user may preview the UI as their own role or a lower one, never higher.
// AUDITOR is a separate, read-only track: an auditor sees only the auditor workspace.
export const ROLE_RANK: Record<UserRole, number> = { FORECASTER: 0, OPERATIONS: 1, MODEL_ANALYST: 2, ADMIN: 3, AUDITOR: 3 };
export const canViewAs = (max: UserRole, target: UserRole): boolean => {
  if (max === 'AUDITOR') return target === 'AUDITOR';
  if (target === 'AUDITOR') return max === 'ADMIN';
  return ROLE_RANK[target] <= ROLE_RANK[max];
};

/** Each role lands on its own workspace after sign-in. */
export const ROLE_HOME: Record<UserRole, string> = {
  FORECASTER: 'control-room', OPERATIONS: 'live-data', MODEL_ANALYST: 'verification', ADMIN: 'governance', AUDITOR: 'audit',
};

export const DASHBOARD_ROUTES = [
  'control-room', 'forecast', 'trust-map', 'fusion', 'regional', 'extremes', 'why-this-forecast',
  'what-changed', 'verification', 'model-performance', 'failure-memory', 'operations', 'live-data', 'experiments',
  'data-health', 'provenance', 'audit', 'governance', 'system-health', 'api-docs', 'settings'
];

const routeFromPath = (fallback: string): string => {
  const seg = window.location.pathname.replace(/^\/dashboard\/?/, '').split('/')[0];
  return DASHBOARD_ROUTES.includes(seg) ? seg : fallback;
};

export const VarunaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [authUser] = useState<AuthUser | null>(() => getStoredUser());
  const maxRole = normalizeRole(getStoredUser()?.role);
  const [role, setRoleState] = useState<UserRole>(maxRole);
  const setRole = (r: UserRole) => {
    // Client-side role switching is a *view filter* only; never escalate above the signed-in role
    if (canViewAs(maxRole, r)) setRoleState(r);
  };
  const can = (perm: string) => hasPermission(authUser, perm);
  const [dataSourcePref, setDataSourcePrefState] = useState<DataSourcePref>(() => {
    try { return (localStorage.getItem('varuna_source') as DataSourcePref) || 'auto'; } catch { return 'auto'; }
  });
  const setDataSourcePref = (p: DataSourcePref) => {
    setDataSourcePrefState(p);
    try { localStorage.setItem('varuna_source', p); } catch { /* ignore */ }
  };
  const [notifications, setNotifications] = useState<VarunaNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const refreshNotifications = async () => {
    if (!hasPermission(authUser, 'notifications:view') || authUser?.offline) return;
    try {
      const r = await listNotifications(30);
      setNotifications(r.items);
      setUnreadCount(r.unread);
    } catch { /* bell stays quiet when the backend is unreachable */ }
  };
  const [regionId, setRegionId] = useState<string>('IN_TELANGANA_DECCAN');
  const [variable, setVariable] = useState<VariableType>('rainfall');
  const [leadHours, setLeadHours] = useState<LeadHours>(48);
  const [weatherRegime, setWeatherRegime] = useState<WeatherRegime>('HEAVY_RAINFALL');
  
  // Deep-linkable dashboard pages: /dashboard/<route> (browser back/forward + shareable URLs)
  const [activeRoute, setActiveRouteState] = useState<string>(() => routeFromPath(ROLE_HOME[maxRole]));
  const setActiveRoute = (route: string) => {
    setActiveRouteState(route);
    const target = `/dashboard/${route}`;
    if (window.location.pathname !== target) window.history.pushState({}, '', target);
    window.scrollTo({ top: 0 });
  };
  useEffect(() => {
    const onPop = () => setActiveRouteState(routeFromPath(ROLE_HOME[maxRole]));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [benchmark, setBenchmark] = useState<BenchmarkSummary | null>(null);
  useEffect(() => {
    // Measured (not hard-coded) benchmark numbers for badges across the UI
    fetch(`${((import.meta as any).env?.VITE_API_BASE as string) || '/api'}/verification/summary`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => d && setBenchmark({
        ml_pct: d.adaptive_advantage_mae_reduction_pct,
        stacking_pct: d.stacking_advantage_mae_reduction_pct,
        best_method: d.best_method,
        test_days: d.sample_size,
      }))
      .catch(() => undefined);
  }, []);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [summary, setSummary] = useState<DashboardSummary>(() => {
    const s = getFallbackDashboard(regionId, variable, leadHours, weatherRegime);
    return { ...s, data_mode: 'DEMO' };
  });
  const [forecastPackage, setForecastPackage] = useState<ForecastIntelligencePackage | null>(null);
  const [dataMode, setDataMode] = useState<DataMode>('DEMO');
  const [dataSourceStatus, setDataSourceStatus] = useState<DataSourceStatus>({
    backendConnected: false,
    provenance: 'CONTROLLED_SYNTHETIC_BENCHMARK',
    lastUpdated: new Date().toISOString(),
    warning: 'BACKEND UNAVAILABLE - DISPLAYING CONTROLLED SYNTHETIC DEMO',
    dataMode: 'DEMO'
  });
  
  const [activeTraceModel, setActiveTraceModel] = useState<ModelId | null>(null);
  const [selectedSubdivision, setSelectedSubdivision] = useState<IndianSubdivision | null>(null);
  const [isFailureModalOpen, setIsFailureModalOpen] = useState<boolean>(false);
  const [isDemoModalOpen, setIsDemoModalOpen] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [isControlRoomFullscreen, setIsControlRoomFullscreen] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [simulatedDisabledModel, setSimulatedDisabledModel] = useState<ModelId | null>(null);

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      const saved = localStorage.getItem('varuna_theme');
      if (saved === 'light' || saved === 'dark') return saved;
    } catch { /* storage unavailable */ }
    // No saved preference: follow the OS setting
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    try { localStorage.setItem('varuna_theme', theme); } catch { /* ignore */ }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const refreshData = async () => {
    setIsLoading(true);
    try {
      // Try fetching backend forecast package first
      let pkg: ForecastIntelligencePackage | null = null;
      try {
        pkg = await fetchForecastPackage(regionId, variable, leadHours, weatherRegime, simulatedDisabledModel || undefined);
        setForecastPackage(pkg);
      } catch (e) {
        setForecastPackage(null);
      }

      const data = await fetchDashboardSummary(regionId, variable, leadHours, weatherRegime, simulatedDisabledModel || undefined, dataSourcePref);
      if (data.notification_id) refreshNotifications();
      const isBackendLive = data.data_mode === 'LIVE';
      
      const currentMode: DataMode = isBackendLive ? 'LIVE' : 'DEMO';
      setDataMode(currentMode);
      setDataSourceStatus({
        backendConnected: isBackendLive,
        provenance: isBackendLive ? (data.provenance || 'DATABASE_VERIFIED') : 'CONTROLLED_SYNTHETIC_BENCHMARK',
        lastUpdated: new Date().toISOString(),
        warning: isBackendLive ? undefined : 'BACKEND UNAVAILABLE - DISPLAYING CONTROLLED SYNTHETIC DEMO',
        dataMode: currentMode
      });
      
      // If a model is simulated offline locally in demo mode
      if (simulatedDisabledModel && !isBackendLive) {
        const remaining = data.weights.filter(w => w.model_id !== simulatedDisabledModel);
        const totalRemaining = remaining.reduce((acc, curr) => acc + curr.weight, 0);
        
        const rebalancedWeights = data.weights.map(w => {
          if (w.model_id === simulatedDisabledModel) {
            return { ...w, weight: 0, status: 'DISABLED' as const, notes: ['CLIENT-SIDE DEMO SIMULATION'] };
          }
          const normalized = totalRemaining > 0 ? Number((w.weight / totalRemaining).toFixed(4)) : 0.33;
          return { ...w, weight: normalized, status: 'ACTIVE' as const };
        });

        let newFused = 0;
        rebalancedWeights.forEach(w => {
          newFused += (data.model_forecasts[w.model_id] || 0) * w.weight;
        });

        setSummary({
          ...data,
          data_mode: 'DEMO',
          weights: rebalancedWeights,
          fused_forecast: Number(newFused.toFixed(1)),
          uncertainty: {
            ...data.uncertainty,
            confidence: 'MEDIUM'
          }
        });
      } else {
        setSummary(data);
      }
    } catch (e) {
      console.error('Failed to refresh data', e);
      setDataMode('DEMO');
      setDataSourceStatus({
        backendConnected: false,
        provenance: 'CONTROLLED_SYNTHETIC_BENCHMARK',
        lastUpdated: new Date().toISOString(),
        warning: 'BACKEND UNAVAILABLE - DISPLAYING CONTROLLED SYNTHETIC DEMO',
        dataMode: 'DEMO'
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, [regionId, variable, leadHours, weatherRegime, simulatedDisabledModel, dataSourcePref]);

  // Notification bell: initial load + gentle polling (60 s)
  useEffect(() => {
    refreshNotifications();
    const t = window.setInterval(refreshNotifications, 60000);
    return () => window.clearInterval(t);
  }, []);

  // Global key listener for Ctrl+K command palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <VarunaContext.Provider
      value={{
        role,
        setRole,
        regionId,
        setRegionId,
        variable,
        setVariable,
        leadHours,
        setLeadHours,
        weatherRegime,
        setWeatherRegime,
        summary,
        subdivisions: fallbackSubdivisions,
        isLoading,
        refreshData,
        dataMode,
        dataSourceStatus,
        forecastPackage,
        activeRoute,
        setActiveRoute,
        activeTraceModel,
        setActiveTraceModel,
        selectedSubdivision,
        setSelectedSubdivision,
        isFailureModalOpen,
        setIsFailureModalOpen,
        isDemoModalOpen,
        setIsDemoModalOpen,
        isCommandPaletteOpen,
        setIsCommandPaletteOpen,
        isControlRoomFullscreen,
        setIsControlRoomFullscreen,
        isUploadModalOpen,
        setIsUploadModalOpen,
        simulatedDisabledModel,
        setSimulatedDisabledModel,
        simulateModelDropout: (m: ModelId = 'WRF') => setSimulatedDisabledModel(m),
        resetFailureState: () => setSimulatedDisabledModel(null),
        isModelDropoutActive: simulatedDisabledModel !== null,
        weights: summary.weights,
        theme,
        toggleTheme,
        maxRole,
        benchmark,
        isSidebarCollapsed,
        setIsSidebarCollapsed,
        isMobileNavOpen,
        setIsMobileNavOpen,
        authUser,
        logout: () => { logoutUser(); window.location.reload(); },
        can,
        dataSourcePref,
        setDataSourcePref,
        notifications,
        unreadCount,
        refreshNotifications,
      }}
    >
      {children}
    </VarunaContext.Provider>
  );
};

export const useVaruna = (): VarunaContextType => {
  const context = useContext(VarunaContext);
  if (!context) {
    throw new Error('useVaruna must be used within a VarunaProvider');
  }
  return context;
};

