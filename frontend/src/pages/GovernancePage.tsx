import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import {
  approveProposal, createProposal, createUser, getGovernanceConfig, getRoleMatrix, listProposals, listUsers,
  rejectProposal, updateUser,
} from '../services/platform';
import { fmtTime } from '../utils/models';
import { ShieldCheck, UserPlus, GitPullRequest, Settings2 } from 'lucide-react';

const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';
const input = 'px-2 py-1 rounded border border-outline-variant/40 bg-surface text-on-surface';
const STATUS: Record<string, string> = {
  PENDING: 'text-amber-700 dark:text-amber-400', APPLIED: 'text-emerald-700 dark:text-emerald-400',
  REJECTED: 'text-rose-700 dark:text-rose-400', FAILED: 'text-rose-700 dark:text-rose-400',
};

const Proposals: React.FC = () => {
  const { can, regionId, variable, leadHours } = useVaruna();
  const [items, setItems] = useState<any[]>([]);
  const [types, setTypes] = useState<Record<string, string>>({});
  const [ct, setCt] = useState('SET_DEFAULT_STRATEGY');
  const [strategy, setStrategy] = useState('BIAS_CORRECTED_STACK');
  const [just, setJust] = useState('');
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const load = () => listProposals().then(setItems).catch(e => setMsg(e.message));
  useEffect(() => { load(); getGovernanceConfig().then(c => setTypes(c.change_types)).catch(() => undefined); }, []);

  const submit = async () => {
    setMsg(null);
    const payload = ct === 'SET_DEFAULT_STRATEGY' ? { strategy } : ct === 'RECALIBRATE_SKILL' ? { region_id: regionId, variable, lead_hours: leadHours } : {};
    try { await createProposal(ct, payload, just); setJust(''); setMsg('Proposal submitted for administrator review.'); load(); }
    catch (e: any) { setMsg(e.message); }
  };
  const review = async (id: string, approve: boolean) => {
    setMsg(null);
    try { await (approve ? approveProposal : rejectProposal)(id, reasons[id] || ''); load(); }
    catch (e: any) { setMsg(e.message); }
  };

  return (
    <div className="flex flex-col gap-4">
      {can('change:propose') && (
        <div className={card}>
          <div className="font-bold text-sm mb-2 flex items-center gap-1.5"><GitPullRequest className="w-4 h-4" /> Propose a scientific change</div>
          <div className="flex flex-wrap gap-2 items-end">
            <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Change</span>
              <select value={ct} onChange={e => setCt(e.target.value)} className={input}>
                {Object.keys(types).map(t => <option key={t} value={t}>{t}</option>)}
              </select></label>
            {ct === 'SET_DEFAULT_STRATEGY' && (
              <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Strategy</span>
                <select value={strategy} onChange={e => setStrategy(e.target.value)} className={input}>
                  <option>ADAPTIVE_ML</option><option>ADAPTIVE_RELIABILITY</option><option>BIAS_CORRECTED_STACK</option>
                </select></label>
            )}
            {ct === 'RECALIBRATE_SKILL' && <span className="text-on-surface-variant">for {regionId} / {variable} / {leadHours} h</span>}
            <label className="flex flex-col gap-0.5 flex-1 min-w-[220px]"><span className="text-[10px] text-on-surface-variant">Evidence / justification (min 10 chars)</span>
              <input value={just} onChange={e => setJust(e.target.value)} className={input} placeholder="e.g. backfill hold-out: stacking MAE 4.1 vs average 5.0 (n=18)" /></label>
            <button disabled={just.length < 10} onClick={submit} className="px-3 py-1 rounded bg-primary text-on-primary font-bold disabled:opacity-40">Submit</button>
          </div>
          <div className="text-[10px] text-on-surface-variant mt-1">{types[ct]}</div>
        </div>
      )}
      {msg && <div className="text-on-surface-variant">{msg}</div>}
      <div className={card}>
        <div className="font-bold text-sm mb-2">Change proposals</div>
        {items.length === 0 ? <div className="text-on-surface-variant">No proposals yet.</div> : (
          <div className="space-y-2">
            {items.map(p => (
              <div key={p.id} className="p-2 rounded bg-surface-container-low">
                <div className="flex flex-wrap items-center gap-2">
                  <strong>{p.change_type}</strong><span className={`font-bold ${STATUS[p.status] || ''}`}>{p.status}</span>
                  <span className="text-[10px] text-on-surface-variant">{p.id} · by {p.proposed_by} · {fmtTime(p.created_at)}</span>
                </div>
                <div className="text-[11px] mt-0.5">payload {JSON.stringify(p.payload)} — {p.justification}</div>
                {p.reviewed_by && <div className="text-[10px] text-on-surface-variant">Reviewed by {p.reviewed_by} {fmtTime(p.reviewed_at)}: {p.review_reason}{p.result ? ` · result ${JSON.stringify(p.result).slice(0, 160)}` : ''}</div>}
                {p.status === 'PENDING' && can('change:approve') && (
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    <input value={reasons[p.id] || ''} onChange={e => setReasons({ ...reasons, [p.id]: e.target.value })} placeholder="review reason (required)" className={`${input} flex-1 min-w-[180px]`} />
                    <button disabled={(reasons[p.id] || '').length < 3} onClick={() => review(p.id, true)} className="px-2.5 py-1 rounded bg-emerald-600 text-white font-bold disabled:opacity-40">Approve & apply</button>
                    <button disabled={(reasons[p.id] || '').length < 3} onClick={() => review(p.id, false)} className="px-2.5 py-1 rounded border border-rose-500/50 text-rose-700 dark:text-rose-400 font-bold disabled:opacity-40">Reject</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <div className="text-[10px] text-on-surface-variant mt-2">Analysts propose, administrators approve; nobody approves their own proposal. Every step is in the audit trail.</div>
      </div>
    </div>
  );
};

const Users: React.FC = () => {
  const { authUser, subdivisions } = useVaruna();
  const [users, setUsers] = useState<any[]>([]);
  const [form, setForm] = useState({ name: '', email: '', role: 'FORECASTER', organization: '', scope: '*', reason: '' });
  const [created, setCreated] = useState<any>(null);
  const [edit, setEdit] = useState<Record<string, { role?: string; is_active?: boolean; reason: string }>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const load = () => listUsers().then(setUsers).catch(e => setMsg(e.message));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setMsg(null); setCreated(null);
    try {
      const r = await createUser({ name: form.name, email: form.email, role: form.role, organization: form.organization || undefined,
        region_scope: form.scope === '*' ? ['*'] : [form.scope], reason: form.reason || undefined });
      setCreated(r); setForm({ ...form, name: '', email: '', reason: '' }); load();
    } catch (e: any) { setMsg(e.message); }
  };
  const save = async (id: string) => {
    const e = edit[id];
    try { await updateUser(id, { role: e.role, is_active: e.is_active, reason: e.reason }); setEdit({ ...edit, [id]: undefined as any }); load(); }
    catch (er: any) { setMsg(er.message); }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className={card}>
        <div className="font-bold text-sm mb-2 flex items-center gap-1.5"><UserPlus className="w-4 h-4" /> Create account (no public sign-up)</div>
        <div className="flex flex-wrap gap-2 items-end">
          <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Full name" className={input} />
          <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="name@organisation.gov.in" className={input} />
          <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} className={input}>
            {['FORECASTER', 'OPERATIONS', 'ANALYST', 'ADMIN', 'AUDITOR'].map(r => <option key={r}>{r}</option>)}
          </select>
          <select value={form.scope} onChange={e => setForm({ ...form, scope: e.target.value })} className={`${input} max-w-[200px]`} title="Region scope">
            <option value="*">All regions</option>
            {subdivisions.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input value={form.organization} onChange={e => setForm({ ...form, organization: e.target.value })} placeholder="Organisation" className={input} />
          <input value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} placeholder="Reason (audited)" className={input} />
          <button disabled={!form.name || !form.email} onClick={submit} className="px-3 py-1 rounded bg-primary text-on-primary font-bold disabled:opacity-40">Create</button>
        </div>
        {created?.initial_password && (
          <div className="mt-2 p-2 rounded border border-amber-500/40 bg-amber-50 dark:bg-amber-950/30">
            One-time initial password for {created.email}: <strong className="select-all">{created.initial_password}</strong> — share it securely; the user must change it at first sign-in. It is not shown again.
          </div>
        )}
      </div>
      {msg && <div className="text-error">{msg}</div>}
      <div className={card}>
        <div className="font-bold text-sm mb-2">Users</div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 min-w-[720px]">
            <thead><tr className="text-left text-on-surface-variant"><th>name</th><th>email</th><th>role</th><th>scope</th><th>active</th><th>last sign-in</th><th>change (reason required)</th></tr></thead>
            <tbody>{users.map(u => {
              const e = edit[u.id];
              const self = u.id === authUser?.user_id;
              return (
                <tr key={u.id} className="border-t border-outline-variant/20 align-top">
                  <td className="py-1">{u.name}</td><td>{u.email}</td><td>{u.role}</td><td>{(u.region_scope || ['*']).join(', ')}</td>
                  <td>{u.is_active ? 'yes' : 'no'}</td><td>{fmtTime(u.last_login_at)}</td>
                  <td>{self ? <span className="text-on-surface-variant">your account</span> : e ? (
                    <div className="flex flex-wrap gap-1">
                      <select value={e.role || u.role} onChange={ev => setEdit({ ...edit, [u.id]: { ...e, role: ev.target.value } })} className={input}>
                        {['FORECASTER', 'OPERATIONS', 'ANALYST', 'ADMIN', 'AUDITOR'].map(r => <option key={r}>{r}</option>)}
                      </select>
                      <label className="flex items-center gap-1"><input type="checkbox" checked={e.is_active ?? u.is_active} onChange={ev => setEdit({ ...edit, [u.id]: { ...e, is_active: ev.target.checked } })} /> active</label>
                      <input value={e.reason} onChange={ev => setEdit({ ...edit, [u.id]: { ...e, reason: ev.target.value } })} placeholder="reason" className={input} />
                      <button disabled={e.reason.length < 3} onClick={() => save(u.id)} className="px-2 py-0.5 rounded bg-primary text-on-primary disabled:opacity-40">Save</button>
                    </div>
                  ) : <button onClick={() => setEdit({ ...edit, [u.id]: { reason: '' } })} className="text-primary">edit</button>}</td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
        <div className="text-[10px] text-on-surface-variant mt-2">Administrators cannot change their own role or deactivate themselves. MFA is the next planned control (see AUDIT_NOTES.md).</div>
      </div>
    </div>
  );
};

const Config: React.FC = () => {
  const [cfg, setCfg] = useState<any>(null);
  const [matrix, setMatrix] = useState<any>(null);
  useEffect(() => { getGovernanceConfig().then(setCfg).catch(() => undefined); getRoleMatrix().then(setMatrix).catch(() => undefined); }, []);
  return (
    <div className="flex flex-col gap-4">
      <div className={card}>
        <div className="font-bold text-sm mb-2">System configuration</div>
        {cfg ? Object.entries(cfg.config).map(([k, v]) => <div key={k}><strong>{k}</strong>: {String(v)}</div>) : '—'}
        <div className="text-[10px] text-on-surface-variant mt-1">Changed only through an approved proposal.</div>
      </div>
      {matrix && (
        <div className={card}>
          <div className="font-bold text-sm mb-2">Role → permission matrix (enforced by the API)</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 min-w-[640px]">
              <thead><tr className="text-left text-on-surface-variant"><th>permission</th>{matrix.roles.map((r: string) => <th key={r} className="text-center">{r}</th>)}</tr></thead>
              <tbody>{Object.entries<string>(matrix.permissions).map(([p, d]) => (
                <tr key={p} className="border-t border-outline-variant/20">
                  <td className="py-0.5" title={d}>{p}</td>
                  {matrix.roles.map((r: string) => <td key={r} className="text-center">{matrix.matrix[r]?.includes(p) ? '✓' : ''}</td>)}
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export const GovernancePage: React.FC = () => {
  const { can } = useVaruna();
  const tabs = [
    { id: 'proposals', label: 'Change proposals', show: can('change:propose') || can('change:approve') || can('audit:view') },
    { id: 'users', label: 'Users', show: can('users:manage') },
    { id: 'config', label: 'Configuration & roles', show: can('config:view') || can('change:propose') },
  ].filter(t => t.show);
  const [tab, setTab] = useState(tabs[0]?.id || 'proposals');
  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 font-mono text-xs text-on-surface">
      <div>
        <h1 className="text-lg font-bold font-sans flex items-center gap-2"><ShieldCheck className="w-5 h-5" /> Governance</h1>
        <p className="text-on-surface-variant font-sans text-sm mt-1 max-w-3xl">
          Separation of duties: administrators manage people and approvals but cannot edit forecasts, skill numbers or the audit trail;
          analysts propose scientific changes; auditors read everything that happened.
        </p>
      </div>
      {tabs.length === 0 ? <div className={card}>Your role has no governance permissions.</div> : (
        <>
          <div className="flex flex-wrap gap-1.5">
            {tabs.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} className={`px-3 py-1 rounded-full border text-xs font-bold flex items-center gap-1 ${tab === t.id ? 'bg-primary text-on-primary border-primary' : 'border-outline-variant/40 text-on-surface hover:bg-surface-container'}`}>
                {t.id === 'config' && <Settings2 className="w-3 h-3" />}{t.label}
              </button>
            ))}
          </div>
          {tab === 'proposals' && <Proposals />}
          {tab === 'users' && <Users />}
          {tab === 'config' && <Config />}
        </>
      )}
    </div>
  );
};
