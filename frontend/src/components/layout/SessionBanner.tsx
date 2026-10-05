import React, { useEffect, useState } from 'react';
import { useVaruna } from '../../context/VarunaContext';
import { SESSION_EXPIRED_EVENT, logoutUser } from '../../services/auth';
import { WifiOff, LogIn, RefreshCw } from 'lucide-react';

const API_BASE: string = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';

/**
 * Tells the user, in plain words, when the session cannot reach or is not accepted by the server:
 * - offline demo session (the server was unreachable at sign-in): read-only, with a reconnect button;
 * - expired / rejected session (any API call answered 401): sign in again.
 */
export const SessionBanner: React.FC<{ onLogout?: () => void }> = ({ onLogout }) => {
  const { authUser } = useVaruna();
  const [expired, setExpired] = useState(false);
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    const on = () => setExpired(true);
    window.addEventListener(SESSION_EXPIRED_EVENT, on);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, on);
  }, []);

  const signInAgain = () => {
    if (onLogout) onLogout();
    else { logoutUser(); window.location.assign('/login'); }
  };

  const reconnect = async () => {
    setChecking(true); setNote(null);
    try {
      const r = await fetch(`${API_BASE}/health`);
      if (r.ok) { signInAgain(); return; }
      setNote(`Server answered HTTP ${r.status}. Try again in a minute.`);
    } catch {
      setNote('Still unreachable. If this is the hosted site, the API may take up to a minute to wake up.');
    }
    setChecking(false);
  };

  if (authUser?.offline) {
    return (
      <div role="status" className="mx-4 lg:mx-6 mt-3 p-3 rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 text-xs font-mono flex flex-wrap items-center gap-2">
        <WifiOff className="w-4 h-4 shrink-0" />
        <span className="flex-1 min-w-[240px]">
          <strong>Offline demo.</strong> The server could not be reached when you signed in, so this session shows built-in synthetic data and cannot upload, fetch or save anything.
          {note && <span className="block mt-1">{note}</span>}
        </span>
        <button onClick={reconnect} disabled={checking} className="flex items-center gap-1 px-2.5 py-1 rounded border border-amber-600/60 font-bold hover:bg-amber-100 dark:hover:bg-amber-900/40 disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} /> Reconnect
        </button>
      </div>
    );
  }
  if (expired) {
    return (
      <div role="alert" className="mx-4 lg:mx-6 mt-3 p-3 rounded-lg border border-error/50 bg-error/10 text-error text-xs font-mono flex flex-wrap items-center gap-2">
        <span className="flex-1 min-w-[240px]"><strong>Session expired.</strong> The server no longer accepts this sign-in (sessions last 24 h). Sign in again to continue; nothing has been lost.</span>
        <button onClick={signInAgain} className="flex items-center gap-1 px-2.5 py-1 rounded border border-error/60 font-bold hover:bg-error/10">
          <LogIn className="w-3.5 h-3.5" /> Sign in again
        </button>
      </div>
    );
  }
  return null;
};
