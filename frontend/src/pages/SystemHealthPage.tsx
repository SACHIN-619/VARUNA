import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { getLiveCatalog } from '../services/platform';
import { RefreshCw, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

const API_BASE: string = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';
const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';

interface Probe { name: string; ok: boolean | null; ms: number | null; detail: string }

async function timed(path: string): Promise<{ ok: boolean; ms: number; body: any }> {
  const t0 = performance.now();
  try {
    const r = await fetch(`${API_BASE}${path}`);
    const body = await r.json().catch(() => null);
    return { ok: r.ok, ms: performance.now() - t0, body };
  } catch {
    return { ok: false, ms: performance.now() - t0, body: null };
  }
}

/** Everything on this page is measured from the browser at load time — no hard-coded telemetry. */
export const SystemHealthPage: React.FC = () => {
  const { summary } = useVaruna();
  const [probes, setProbes] = useState<Probe[]>([]);
  const [ready, setReady] = useState<any>(null);
  const [checkedAt, setCheckedAt] = useState<string>('');
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    const [h, r, s] = await Promise.all([timed('/health'), timed('/ready'), timed('/dashboard/summary?source=demo')]);
    let live: Probe = { name: 'Live data connector', ok: null, ms: null, detail: 'not checked' };
    try {
      const t0 = performance.now();
      const c = await getLiveCatalog();
      live = { name: 'Live data connector', ok: c.enabled, ms: performance.now() - t0, detail: c.enabled ? 'enabled (network reachability is tested on fetch)' : c.status };
    } catch (e: any) { live = { name: 'Live data connector', ok: false, ms: null, detail: e.message }; }
    setReady(r.body);
    setProbes([
      { name: 'API liveness (/api/health)', ok: h.ok, ms: h.ms, detail: h.body ? `v${h.body.version} · ${h.body.environment} · DB ${h.body.database}` : 'unreachable' },
      { name: 'Readiness (/api/ready)', ok: r.ok, ms: r.ms, detail: r.body ? `${r.body.status} · server-side ${r.body.execution_time_ms} ms` : 'unreachable' },
      { name: 'Pipeline round trip (14 stages, demo inputs)', ok: s.ok, ms: s.ms,
        detail: s.body?.stage_trace ? `server stages ${s.body.stage_trace.reduce((a: number, t: any) => a + t.duration_ms, 0).toFixed(1)} ms` : 'no trace' },
      live,
    ]);
    setCheckedAt(new Date().toISOString().slice(11, 19) + ' UTC');
    setBusy(false);
  };
  useEffect(() => { run(); }, []);

  const Icon = ({ ok }: { ok: boolean | null }) => ok === null ? <AlertTriangle className="w-4 h-4 text-amber-600" /> : ok ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-rose-600" />;

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 font-mono text-xs text-on-surface">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold font-sans">System health</h1>
          <p className="text-on-surface-variant font-sans text-sm mt-1">Measured from your browser when the page loads{checkedAt ? ` (last check ${checkedAt})` : ''}. Latency includes the network.</p>
        </div>
        <button onClick={run} disabled={busy} className="px-3 py-1.5 rounded border border-primary/50 text-primary font-bold flex items-center gap-1 disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 ${busy ? 'animate-spin' : ''}`} /> Re-check
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {probes.map(p => (
          <div key={p.name} className={card}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold flex items-center gap-1.5"><Icon ok={p.ok} />{p.name}</span>
              <span className="text-on-surface-variant">{p.ms != null ? `${p.ms.toFixed(0)} ms` : '—'}</span>
            </div>
            <div className="text-on-surface-variant mt-1 break-all">{p.detail}</div>
          </div>
        ))}
      </div>

      {ready?.subsystems && (
        <div className={card}>
          <div className="font-bold text-sm mb-2">Subsystems reported by /api/ready</div>
          {Object.entries<any>(ready.subsystems).map(([k, v]) => (
            <div key={k} className="py-1 border-t border-outline-variant/20 first:border-0">
              <strong>{k}</strong>: <span className="text-on-surface-variant break-all">{JSON.stringify(v)}</span>
            </div>
          ))}
        </div>
      )}

      <div className={card}>
        <div className="font-bold text-sm mb-1">Current forecast run</div>
        <div className="text-on-surface-variant">
          run {summary.run_id || '—'} · {(summary.stage_trace || []).length} stages ·
          {' '}{(summary.stage_trace || []).reduce((a, t) => a + t.duration_ms, 0).toFixed(1)} ms server time · source {summary.source_mode || 'offline'}
        </div>
      </div>
    </div>
  );
};
