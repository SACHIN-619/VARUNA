import React, { useEffect, useRef, useState } from 'react';
import { useVaruna, canViewAs } from '../../context/VarunaContext';
import { logoutUser } from '../../services/auth';
import { Search, Sun, Moon, Upload, LogOut, Menu, ChevronDown, Home, CheckCircle2, User } from 'lucide-react';
import { UserRole } from '../../types';
import { NotificationBell } from './NotificationBell';

interface NavbarProps {
  onViewLanding?: () => void;
  onLogout?: () => void;
}

const ROLES: Array<{ id: UserRole; label: string; desc: string }> = [
  { id: 'FORECASTER', label: 'Forecaster', desc: 'Forecast, fusion, explanations, verification' },
  { id: 'OPERATIONS', label: 'Operations', desc: 'Data sources, live fetch, feed health' },
  { id: 'MODEL_ANALYST', label: 'Model analyst', desc: 'Skill, experiments, change proposals' },
  { id: 'ADMIN', label: 'Administrator', desc: 'Users, approvals, configuration' },
  { id: 'AUDITOR', label: 'Auditor', desc: 'Read-only audit trail & evidence' },
];

/**
 * Compact top bar. Forecast filters live in the ContextBar below it, so nothing here needs to
 * hide at narrow widths or high zoom: every control is an icon button with an accessible label.
 */
export const Navbar: React.FC<NavbarProps> = ({ onViewLanding, onLogout }) => {
  const {
    role, setRole, theme, toggleTheme, setIsCommandPaletteOpen, setIsUploadModalOpen, maxRole,
    isMobileNavOpen, setIsMobileNavOpen, authUser, can,
  } = useVaruna();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [menuOpen]);

  const current = ROLES.find(r => r.id === role) || ROLES[0];
  const signOut = () => { if (onLogout) onLogout(); else { logoutUser(); window.location.reload(); } };
  const iconBtn = 'p-1.5 rounded bg-surface-container-low hover:bg-surface-container text-on-surface-variant border border-outline-variant/30 shrink-0';

  return (
    <header className="fixed top-0 left-0 right-0 h-14 z-50 bg-surface-container-lowest/95 backdrop-blur-md border-b border-outline-variant/30 flex items-center justify-between gap-2 px-3 lg:px-5">
      <div className="flex items-center gap-2.5 min-w-0">
        <button onClick={() => setIsMobileNavOpen(!isMobileNavOpen)} className={`lg:hidden ${iconBtn}`} aria-label="Toggle navigation">
          <Menu className="w-4 h-4" />
        </button>
        <div className="w-8 h-8 rounded bg-gradient-to-tr from-[#006194] to-[#39b8fd] flex items-center justify-center text-white font-bold text-lg shrink-0">V</div>
        <div className="flex flex-col min-w-0 leading-tight">
          <span className="font-bold text-sm tracking-tight text-on-surface truncate">VARUNA <span className="hidden sm:inline font-semibold text-primary">· Forecast Intelligence</span></span>
          <span className="hidden md:block font-mono text-[10px] text-on-surface-variant truncate">SIH26081 · research prototype · not an official warning service</span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        {can('data:ingest') && (
          <button onClick={() => setIsUploadModalOpen(true)} className={iconBtn} aria-label="Upload dataset" title="Upload a dataset (CSV / JSON / Parquet / NetCDF / ZIP)">
            <Upload className="w-4 h-4" />
          </button>
        )}
        <button onClick={() => setIsCommandPaletteOpen(true)} className={iconBtn} aria-label="Search (Ctrl+K)" title="Search pages (Ctrl+K)">
          <Search className="w-4 h-4" />
        </button>
        <NotificationBell />
        <button onClick={toggleTheme} className={iconBtn} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </button>

        <div className="relative" ref={menuRef}>
          <button onClick={() => setMenuOpen(o => !o)} className="flex items-center gap-1.5 pl-1 pr-2 py-1 rounded-full border border-outline-variant/40 hover:bg-surface-container" aria-haspopup="menu" aria-expanded={menuOpen}>
            <span className="w-6 h-6 rounded-full bg-primary text-on-primary flex items-center justify-center"><User className="w-3.5 h-3.5" /></span>
            <span className="hidden md:inline font-mono text-[11px] font-bold text-on-surface max-w-[120px] truncate">{current.label}</span>
            <ChevronDown className="w-3 h-3 text-on-surface-variant" />
          </button>
          {menuOpen && (
            <div role="menu" className="absolute right-0 top-full mt-1.5 w-64 bg-surface-container-lowest rounded-xl shadow-xl border border-outline-variant/30 p-1.5 z-50 font-mono text-xs">
              <div className="px-2 py-1.5 border-b border-outline-variant/20 mb-1">
                <div className="font-bold text-on-surface truncate">{authUser?.name || 'Signed-in user'}</div>
                <div className="text-[10px] text-on-surface-variant truncate">{authUser?.email}</div>
                <div className="text-[10px] text-on-surface-variant">Signed in as {ROLES.find(r => r.id === maxRole)?.label}{authUser?.offline ? ' · offline demo' : ''}</div>
              </div>
              <div className="px-2 pt-1 text-[10px] text-on-surface-variant uppercase font-bold">View as</div>
              {ROLES.filter(r => canViewAs(maxRole, r.id)).map(r => (
                <button key={r.id} role="menuitem" onClick={() => { setRole(r.id); setMenuOpen(false); }}
                  className={`w-full text-left px-2 py-1.5 rounded-lg flex flex-col ${role === r.id ? 'bg-primary text-on-primary' : 'hover:bg-surface-container-low text-on-surface'}`}>
                  <span className="flex items-center justify-between font-bold">{r.label}{role === r.id && <CheckCircle2 className="w-3.5 h-3.5" />}</span>
                  <span className={`text-[10px] ${role === r.id ? 'opacity-80' : 'text-on-surface-variant'}`}>{r.desc}</span>
                </button>
              ))}
              <div className="text-[9px] text-on-surface-variant px-2 pb-1">Viewing as another role filters the menu only; the server still enforces your own permissions.</div>
              <div className="border-t border-outline-variant/20 mt-1 pt-1">
                {onViewLanding && (
                  <button role="menuitem" onClick={() => { setMenuOpen(false); onViewLanding(); }} className="w-full text-left px-2 py-1.5 rounded-lg hover:bg-surface-container-low text-on-surface flex items-center gap-2">
                    <Home className="w-3.5 h-3.5" /> Home page
                  </button>
                )}
                <button role="menuitem" onClick={signOut} className="w-full text-left px-2 py-1.5 rounded-lg hover:bg-error/10 text-error flex items-center gap-2 font-bold">
                  <LogOut className="w-3.5 h-3.5" /> Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
