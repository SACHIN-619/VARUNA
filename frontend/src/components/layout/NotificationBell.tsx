import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Bell, X, CheckCheck } from 'lucide-react';
import { useVaruna } from '../../context/VarunaContext';
import { getNotification, markAllNotificationsRead, markNotificationRead, VarunaNotification } from '../../services/platform';
import { fmtTime, modelInfo } from '../../utils/models';

const SEV: Record<string, string> = {
  CRITICAL: 'bg-rose-600 text-white',
  WARNING: 'bg-amber-500 text-slate-900',
  INFO: 'bg-sky-600 text-white',
};

const Detail: React.FC<{ id: string; onClose: () => void }> = ({ id, onClose }) => {
  const [n, setN] = useState<VarunaNotification | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { getNotification(id).then(setN).catch(e => setErr(e.message)); }, [id]);
  // Portal: the navbar uses backdrop-blur, which would otherwise become the containing block of `fixed`
  return createPortal(
    <div className="fixed inset-0 z-[150] bg-black/40 flex items-center justify-center p-3" onClick={onClose}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl bg-surface-container-lowest border border-outline-variant/40 shadow-2xl p-4 font-mono text-xs text-on-surface">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            {n && <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${SEV[n.severity]}`}>{n.severity}</span>}
            <div className="text-sm font-bold mt-1">{n?.title || 'Loading…'}</div>
            {n && <div className="text-[10px] text-on-surface-variant">Raised {fmtTime(n.created_at)} · {n.math?.source_mode} · strategy {n.math?.strategy}</div>}
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-surface-container" aria-label="Close"><X className="w-4 h-4" /></button>
        </div>
        {err && <div className="text-error">{err}</div>}
        {n && (
          <>
            <div className="text-[10px] font-bold uppercase text-on-surface-variant mt-2 mb-1">Rules evaluated</div>
            <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5">
              <thead><tr className="text-on-surface-variant text-left"><th>rule</th><th>formula</th><th>computation</th><th>fired</th></tr></thead>
              <tbody>
                {(n.math?.rules || []).map(r => (
                  <tr key={r.rule} className={`border-t border-outline-variant/20 align-top ${r.triggered ? '' : 'opacity-60'}`}>
                    <td className="pr-2 py-1 font-bold whitespace-nowrap">{r.rule.replace(/^R\d_/, '')}</td>
                    <td className="pr-2 py-1">{r.formula}</td>
                    <td className="pr-2 py-1 break-all">{r.computation}</td>
                    <td className="py-1">{r.triggered ? 'yes' : 'no'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(['previous', 'current'] as const).map(k => (
              <div key={k}>
                <div className="text-[10px] font-bold uppercase text-on-surface-variant mt-3 mb-1">
                  {k} inputs · snapshot {fmtTime(k === 'previous' ? n.math?.previous_at : n.math?.current_at)}
                </div>
                <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5">
                  <thead><tr className="text-on-surface-variant text-left"><th>model</th><th className="text-right">value</th><th className="text-right">weight</th><th>source</th><th>issued</th><th>received</th></tr></thead>
                  <tbody>
                    {(n.sources?.[k] || []).map(s => (
                      <tr key={s.model_id} className="border-t border-outline-variant/20">
                        <td className="pr-2 py-0.5">{modelInfo(s.model_id).label}</td>
                        <td className="pr-2 text-right">{s.value ?? '—'}</td>
                        <td className="pr-2 text-right">{s.weight != null ? (s.weight * 100).toFixed(1) + '%' : '—'}</td>
                        <td className="pr-2 break-all">{s.source}</td>
                        <td className="pr-2 whitespace-nowrap">{fmtTime(s.issue_time)}</td>
                        <td className="whitespace-nowrap">{fmtTime(s.received_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </>
        )}
      </div>
    </div>,
    document.body
  );
};

export const NotificationBell: React.FC = () => {
  const { notifications, unreadCount, refreshNotifications, can } = useVaruna();
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  if (!can('notifications:view')) return null;

  const openDetail = async (n: VarunaNotification) => {
    setDetail(n.id);
    setOpen(false);
    if (!n.read) { try { await markNotificationRead(n.id); refreshNotifications(); } catch { /* ignore */ } }
  };

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => { setOpen(o => !o); if (!open) refreshNotifications(); }}
        className="relative p-1.5 rounded bg-surface-container-low hover:bg-surface-container text-on-surface-variant border border-outline-variant/30"
        aria-label={`Notifications (${unreadCount} unread)`} title="Forecast-change notifications">
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-error text-on-error text-[9px] font-bold flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-[min(92vw,380px)] max-h-[70vh] overflow-y-auto bg-surface-container-lowest rounded-xl shadow-xl border border-outline-variant/30 z-50 font-mono text-xs">
          <div className="flex items-center justify-between px-3 py-2 border-b border-outline-variant/30 sticky top-0 bg-surface-container-lowest">
            <span className="font-bold text-on-surface">Forecast changes</span>
            {unreadCount > 0 && (
              <button onClick={async () => { await markAllNotificationsRead().catch(() => undefined); refreshNotifications(); }}
                className="flex items-center gap-1 text-[10px] text-primary"><CheckCheck className="w-3 h-3" /> mark all read</button>
            )}
          </div>
          {notifications.length === 0 ? (
            <div className="p-3 text-on-surface-variant">No changes yet. A notification is raised when a new run differs from the previous one by more than the rule thresholds (fused jump, alert level, dominant model, confidence, weight shift).</div>
          ) : notifications.map(n => (
            <button key={n.id} onClick={() => openDetail(n)} className={`w-full text-left px-3 py-2 border-b border-outline-variant/15 hover:bg-surface-container-low ${n.read ? 'opacity-70' : ''}`}>
              <div className="flex items-center gap-1.5">
                <span className={`px-1 rounded text-[9px] font-bold ${SEV[n.severity]}`}>{n.severity}</span>
                {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
                <span className="text-[10px] text-on-surface-variant ml-auto">{fmtTime(n.created_at)}</span>
              </div>
              <div className="mt-0.5 font-semibold text-on-surface truncate">{n.title}</div>
              <div className="text-[10px] text-on-surface-variant line-clamp-2">{n.message}</div>
            </button>
          ))}
        </div>
      )}
      {detail && <Detail id={detail} onClose={() => setDetail(null)} />}
    </div>
  );
};
