import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { listAuditEvents, verifyAuditChain } from '../services/platform';
import { fmtTime } from '../utils/models';
import { ShieldCheck, ShieldAlert, Lock, RefreshCw } from 'lucide-react';

const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';
const PAGE = 50;

/** Real, append-only, hash-chained audit trail (read-only for everyone, including administrators). */
export const AuditLogPage: React.FC = () => {
  const { can } = useVaruna();
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState('');
  const [actor, setActor] = useState('');
  const [result, setResult] = useState('');
  const [chain, setChain] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = (off = offset) => {
    setLoading(true);
    const p: Record<string, string | number> = { limit: PAGE, offset: off };
    if (action) p.action = action;
    if (actor) p.actor = actor;
    if (result) p.result = result;
    listAuditEvents(p).then(r => { setItems(r.items); setTotal(r.total); setErr(null); })
      .catch(e => setErr(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { if (can('audit:view')) load(0); }, []);

  if (!can('audit:view')) {
    return <div className="p-6"><div className={`${card} flex items-center gap-2 text-sm`}><Lock className="w-4 h-4" /> The audit trail is visible to administrators and auditors.</div></div>;
  }

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 font-mono text-xs text-on-surface">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold font-sans">Audit trail</h1>
          <p className="text-on-surface-variant font-sans text-sm mt-1 max-w-3xl">
            Every sign-in, denied access, data ingest, live fetch, verification, skill update, user change and approval is appended here.
            Each entry stores the SHA-256 of its content plus the previous entry's hash, so any edit breaks the chain. Rows cannot be updated or deleted through the application.
          </p>
        </div>
        <button onClick={() => verifyAuditChain().then(setChain).catch(e => setErr(e.message))}
          className="px-3 py-1.5 rounded bg-primary text-on-primary font-bold flex items-center gap-1"><ShieldCheck className="w-4 h-4" /> Verify integrity</button>
      </div>

      {chain && (
        <div className={`${card} flex items-start gap-2 ${chain.intact ? 'border-emerald-500/40' : 'border-rose-500/50'}`}>
          {chain.intact ? <ShieldCheck className="w-5 h-5 text-emerald-600" /> : <ShieldAlert className="w-5 h-5 text-rose-600" />}
          <div>
            <div className="font-bold">{chain.intact ? `Chain intact · ${chain.checked} entries checked` : `Chain BROKEN at entry #${chain.broken_at_seq}`}</div>
            <div className="text-[10px] text-on-surface-variant break-all">{chain.intact ? `head ${chain.head_hash}` : chain.reason}</div>
          </div>
        </div>
      )}

      <div className={`${card} flex flex-wrap gap-2 items-end`}>
        <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Action</span>
          <select value={action} onChange={e => setAction(e.target.value)} className="px-2 py-1 rounded border border-outline-variant/40 bg-surface">
            <option value="">all</option>
            {['LOGIN', 'LOGIN_FAILED', 'ACCESS_DENIED', 'DATA_INGEST', 'LIVE_FETCH', 'LIVE_BACKFILL', 'VERIFY_RUN', 'SKILL_UPDATE',
              'EXPERIMENT_RUN', 'USER_CREATE', 'USER_UPDATE', 'PASSWORD_CHANGE', 'CHANGE_PROPOSED', 'CHANGE_APPROVE', 'CHANGE_REJECT', 'AUDIT_CHAIN_VERIFY'
            ].map(a => <option key={a}>{a}</option>)}
          </select></label>
        <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Actor contains</span>
          <input value={actor} onChange={e => setActor(e.target.value)} className="px-2 py-1 rounded border border-outline-variant/40 bg-surface" /></label>
        <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Result</span>
          <select value={result} onChange={e => setResult(e.target.value)} className="px-2 py-1 rounded border border-outline-variant/40 bg-surface">
            <option value="">all</option><option>SUCCESS</option><option>DENIED</option><option>FAILED</option>
          </select></label>
        <button onClick={() => { setOffset(0); load(0); }} className="px-3 py-1 rounded border border-primary/50 text-primary font-bold flex items-center gap-1">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Apply
        </button>
        <span className="ml-auto text-on-surface-variant">{total} entries</span>
      </div>

      {err && <div className="text-error">{err}</div>}

      <div className={card}>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 min-w-[760px]">
            <thead><tr className="text-left text-on-surface-variant"><th>#</th><th>time (UTC)</th><th>actor</th><th>role</th><th>action</th><th>entity</th><th>result</th><th>reason</th></tr></thead>
            <tbody>
              {items.map(e => (
                <React.Fragment key={e.seq}>
                  <tr onClick={() => setOpen(open === e.seq ? null : e.seq)} className="border-t border-outline-variant/20 cursor-pointer hover:bg-surface-container-low">
                    <td className="py-1">{e.seq}</td><td className="whitespace-nowrap">{fmtTime(e.timestamp)}</td><td>{e.actor}</td><td>{e.actor_role || '—'}</td>
                    <td className="font-bold">{e.action}</td><td className="break-all">{e.entity_type}{e.entity_id ? ` · ${e.entity_id}` : ''}</td>
                    <td className={e.result === 'SUCCESS' ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'}>{e.result}</td>
                    <td className="max-w-[240px] truncate" title={e.reason || ''}>{e.reason || ''}</td>
                  </tr>
                  {open === e.seq && (
                    <tr className="bg-surface-container-low"><td colSpan={8} className="p-2 text-[10px] break-all">
                      <div>metadata: {JSON.stringify(e.metadata)}</div>
                      <div>ip: {e.request_ip || '—'} · hash {e.hash} · prev {e.prev_hash}</div>
                    </td></tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-between mt-2">
          <button disabled={offset === 0} onClick={() => { const o = Math.max(0, offset - PAGE); setOffset(o); load(o); }} className="px-2 py-0.5 rounded border border-outline-variant/40 disabled:opacity-40">newer</button>
          <button disabled={offset + PAGE >= total} onClick={() => { const o = offset + PAGE; setOffset(o); load(o); }} className="px-2 py-0.5 rounded border border-outline-variant/40 disabled:opacity-40">older</button>
        </div>
      </div>
    </div>
  );
};
