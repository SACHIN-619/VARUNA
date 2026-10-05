import React, { useState, useEffect } from 'react';
import { VarunaProvider, useVaruna } from './context/VarunaContext';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { ContextBar } from './components/layout/ContextBar';
import { CommandPalette } from './components/layout/CommandPalette';
import { FusionTraceDrawer } from './components/drawers/FusionTraceDrawer';
import { RegionDetailDrawer } from './components/drawers/RegionDetailDrawer';
import { FailureSimulationDrawer } from './components/drawers/FailureSimulationDrawer';
import { InteractiveDemoModal } from './components/shared/InteractiveDemoModal';
import { DatasetUploadModal } from './components/shared/DatasetUploadModal';
import { LoginPage } from './pages/LoginPage';
import { LandingPage } from './pages/LandingPage';
import { isAuthenticated, logoutUser, getStoredUser, AuthUser } from './services/auth';

// Pages
import { ControlRoomPage } from './pages/ControlRoomPage';
import { ForecastIntelligencePage } from './pages/ForecastIntelligencePage';
import { ModelTrustMapPage } from './pages/ModelTrustMapPage';
import { FusionCentrePage } from './pages/FusionCentrePage';
import { RegionalDeepDivePage } from './pages/RegionalDeepDivePage';
import { ExtremeEventsPage } from './pages/ExtremeEventsPage';
import { WhyThisForecastPage } from './pages/WhyThisForecastPage';
import { WhatChangedPage } from './pages/WhatChangedPage';
import { VerificationCentrePage } from './pages/VerificationCentrePage';
import { ModelPerformancePage } from './pages/ModelPerformancePage';
import { SessionBanner } from './components/layout/SessionBanner';
import { FailureMemoryPage } from './pages/FailureMemoryPage';
import { OperationsPage } from './pages/OperationsPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { DataHealthPage } from './pages/DataHealthPage';
import { ProvenancePage } from './pages/ProvenancePage';
import { AuditLogPage } from './pages/AuditLogPage';
import { SystemHealthPage } from './pages/SystemHealthPage';
import { ApiDocsPage } from './pages/ApiDocsPage';
import { SettingsPage } from './pages/SettingsPage';
import { LiveDataPage } from './pages/LiveDataPage';
import { GovernancePage } from './pages/GovernancePage';

import { ErrorBoundary } from './components/shared/ErrorBoundary';

interface AppContentProps {
  onViewLanding?: () => void;
  onLogout?: () => void;
}

const AppContent: React.FC<AppContentProps> = ({ onViewLanding, onLogout }) => {
  const { activeRoute, isControlRoomFullscreen, isUploadModalOpen, setIsUploadModalOpen, isSidebarCollapsed } = useVaruna();

  const renderCurrentPage = () => {
    switch (activeRoute) {
      case 'control-room':
        return <ControlRoomPage />;
      case 'forecast':
        return <ForecastIntelligencePage />;
      case 'trust-map':
        return <ModelTrustMapPage />;
      case 'fusion':
        return <FusionCentrePage />;
      case 'regional':
        return <RegionalDeepDivePage />;
      case 'extremes':
        return <ExtremeEventsPage />;
      case 'why-this-forecast':
        return <WhyThisForecastPage />;
      case 'what-changed':
        return <WhatChangedPage />;
      case 'verification':
        return <VerificationCentrePage />;
      case 'model-performance':
        return <ModelPerformancePage />;
      case 'failure-memory':
        return <FailureMemoryPage />;
      case 'operations':
        return <OperationsPage />;
      case 'experiments':
        return <ExperimentsPage />;
      case 'data-health':
        return <DataHealthPage />;
      case 'provenance':
        return <ProvenancePage />;
      case 'audit':
        return <AuditLogPage />;
      case 'system-health':
        return <SystemHealthPage />;
      case 'api-docs':
        return <ApiDocsPage />;
      case 'settings':
        return <SettingsPage />;
      case 'live-data':
        return <LiveDataPage />;
      case 'governance':
        return <GovernancePage />;
      default:
        return <ControlRoomPage />;
    }
  };

  return (
    <div className="min-h-screen bg-surface text-on-surface font-sans antialiased flex flex-col">
      {/* Top Fixed Navbar Header */}
      <Navbar onViewLanding={onViewLanding} onLogout={onLogout} />

      {/* Main Container Layout */}
      <div className="flex flex-1 pt-14">
        {/* Left Collapsible Sidebar Navigation */}
        {!isControlRoomFullscreen && <Sidebar />}

        {/* Dynamic Center Viewport Container */}
        <main className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${!isControlRoomFullscreen ? (isSidebarCollapsed ? 'lg:pl-16' : 'lg:pl-72') : ''}`}>
          {/* Forecast context (filters) — wraps instead of hiding at narrow widths / high zoom */}
          <ContextBar />
          <SessionBanner onLogout={onLogout} />

          {/* Page Viewport */}
          <div className="flex-1 w-full bg-met-grid">
            <ErrorBoundary>
              {renderCurrentPage()}
            </ErrorBoundary>
          </div>

          {/* Minimalist Institutional Footer */}
          <footer className="w-full bg-surface-container-lowest border-t border-outline-variant/30 px-6 py-3 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-on-surface-variant select-none">
            <div className="flex items-center gap-2">
              <span className="font-headline font-bold text-on-surface">VARUNA</span>
              <span>— Adaptive Forecast Intelligence Platform</span>
              <span className="text-outline-variant">•</span>
              <span>SIH26081 • MoES / NCMRWF</span>
            </div>
            <div className="text-[11px]">
              Prototype Decision Support • Provenance displayed at source
            </div>
          </footer>
        </main>
      </div>

      {/* Drawers, Modals & Command Palette Overlays */}
      <FusionTraceDrawer />
      <RegionDetailDrawer />
      <FailureSimulationDrawer />
      <InteractiveDemoModal />
      <DatasetUploadModal isOpen={isUploadModalOpen} onClose={() => setIsUploadModalOpen(false)} />
      <CommandPalette />
    </div>
  );
};

export default function App() {
  const [currentPath, setCurrentPath] = useState<string>(() => window.location.pathname || '/');

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = (path: string) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLogin = (_user: AuthUser) => {
    navigateTo('/dashboard');
  };

  const [, setSessionTick] = useState(0);
  const handleLogout = () => {
    logoutUser();
    setSessionTick(t => t + 1); // re-render even when already on "/"
    navigateTo('/');
  };

  // Auth redirects run in an effect (calling setState/pushState during render triggers
  // React "Cannot update a component while rendering" warnings and double renders).
  const authed = isAuthenticated();
  const redirect =
    currentPath === '/login' && authed ? '/dashboard' :
    currentPath.startsWith('/dashboard') && !authed ? '/login' : null;
  useEffect(() => {
    if (redirect) {
      window.history.replaceState({}, '', redirect);
      setCurrentPath(redirect);
    }
  }, [redirect]);

  // ─── 1. ROUTE: /login ────────────────────────────────────────────────────────
  if (currentPath === '/login') {
    if (redirect) return null;
    return (
      <LoginPage
        onLogin={handleLogin}
        onBackToLanding={() => navigateTo('/')}
      />
    );
  }

  // ─── 2. ROUTE: /dashboard ───────────────────────────────────────────────────
  if (currentPath.startsWith('/dashboard')) {
    if (redirect) return null;
    return (
      <VarunaProvider>
        <AppContent
          onViewLanding={() => navigateTo('/')}
          onLogout={handleLogout}
        />
      </VarunaProvider>
    );
  }

  // ─── 3. DEFAULT ROUTE: / (Home Page / Landing Page) ─────────────────────────
  const user = getStoredUser();
  const loggedIn = isAuthenticated();

  return (
    <LandingPage
      loggedIn={loggedIn}
      userLabel={user ? `${user.name} · ${user.role}` : undefined}
      onSignOut={handleLogout}
      onEnterApp={() => navigateTo(loggedIn ? '/dashboard' : '/login')}
      onOpenLogin={() => navigateTo(loggedIn ? '/dashboard' : '/login')}
      onSelectRole={() => navigateTo(loggedIn ? '/dashboard' : '/login')}
    />
  );
}
