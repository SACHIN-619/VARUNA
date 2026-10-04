import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { liveDatasets, listAuditEvents } from '../services/platform';
import { modelInfo, fmtTime, PROVENANCE_LABEL } from '../utils/models';
import { ShieldAlert, RotateCcw, Radio } from 'lucide-react';
import { ModelId } from '../types';

const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';
const STATE: Record<string, string> = {
  ACCEPTED: 'text-emerald-700 dark:text-emerald-400', WARNING: 'text-amber-700 dark:text-amber-400',
  REJECTED: 'text-rose-700 dark:text-rose-400', QUARANTINED: 'text-purple-700 dark:text-purple-400', MISSING: 'text-on-surface-variant',
};

/** Feed status for the run on screen, recent fetches and the operational event log — all from the API. */
export const OperationsPage: React.FC = () => {
  const { summary, simulatedDisabledModel, simulateModelDropout, resetFailureState, setIsFailureModalOpen, setActiveRoute, can } = useVaruna();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [eventsNote, setEventsNote] = useState<string | null>(null);

  useEffect(() => {
    liveDatasets().then(d => setDatasets(d.slice(0, 8))).catch(() => setDatasets([]));
    if (can('audit:view')) {
      listAuditEvents({ limit: 15 }).then(r => setEvents(r.items.filter(e => ['LIVE_FETCH', 'LIVE_BACKFILL', 'DATA_INGEST', 'VERIFY_RUN', 'SKILL_UPDATE'].includes(e.action))))
        .catch(e => setEventsNote(e.message));
    } else setEventsNote('The operational event log is part of the audit trail (administrators / auditors).');
  }, [summary.run_id]);

  const models = Object.keys(summary.model_forecasts || {});
  const weightOf = (m: string) => summary.weights?.find(w => w.model_id === m)?.weight ?? 0;

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 font-mono text-xs text-on-surface">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold font-sans">Source health & dropout</h1>
          <p className="text-on-surface-variant font-sans text-sm mt-1 max-w-3xl">
            Status of every model feed in the current run, with where each value came from and when. Use the what-if dropout to see how weights re-normalise when a feed fails.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setActiveRoute('live-data')} className="px-3 py-1.5 rounded border border-primary/50 text-primary font-bold flex items-center gap-1"><Radio className="w-3.5 h-3.5" /> Data sources</button>
          <button onClick={() => setIsFailureModalOpen(true)} className="px-3 py-1.5 rounded bg-amber-500 text-slate-950 font-bold flex items-center gap-1"><ShieldAlert className="w-3.5 h-3.5" /> Failure simulator</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {models.map(m => {
          const meta = summary.source_meta?.[m];
          const info = modelInfo(m, meta);
          const state = summary.qc_state?.[m] || (simulatedDisabledModel === m ? 'MISSING' : '—');
          return (
            <div key={m} className={card} style={{ borderLeft: `3px solid ${info.hex}` }}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-sm font-sans">{info.label}</span>
                <span className={`font-bold ${STATE[state] || ''}`}>{simulatedDisabledModel === m ? 'SIMULATED DROPOUT' : state}</span>
              </div>
              <div className="text-[10px] text-on-surface-variant">{info.role}</div>
              <div className="mt-2 space-y-0.5">
                <div className="flex justify-between"><span className="text-on-surface-variant">value</span><span>{(summary.model_forecasts as any)[m] ?? '—'} {summary.unit}</span></div>
                <div className="flex justify-between"><span className="text-on-surface-variant">weight</span><span>{(weightOf(m) * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between gap-2"><span className="text-on-surface-variant">source</span><span className="text-right break-all">{meta?.source || 'synthetic demo scenario'}</span></div>
                <div className="flex justify-between"><span className="text-on-surface-variant">type</span><span>{PROVENANCE_LABEL[meta?.provenance || ''] || meta?.provenance || 'Synthetic demo'}</span></div>
                <div className="flex justify-between"><span className="text-on-surface-variant">issued</span><span>{fmtTime(meta?.issue_time)}</span></div>
                <div className="flex justify-between"><span className="text-on-surface-variant">received</span><span>{fmtTime(meta?.fetched_at)}</span></div>
                {(summary.qc_flags?.[m] || []).length > 0 && <div className="text-amber-700 dark:text-amber-400">flags: {summary.qc_flags![m].join(', ')}</div>}
              </div>
            </div>
          );
        })}
      </div>

      <div className={card}>
        <div className="font-bold text-sm font-sans mb-1">What-if: feed dropout</div>
        <p className="text-on-surface-variant mb-2">Removes one model for this view only; the backend re-runs all 14 stages and re-normalises weights over the remaining models. Nothing is stored and no notification is raised.</p>
        <div className="flex flex-wrap gap-1.5">
          {models.map(m => (
            <button key={m} onClick={() => simulateModelDropout(m as ModelId)}
              className={`px-2.5 py-1 rounded border ${simulatedDisabledModel === m ? 'border-rose-500 text-rose-700 dark:text-rose-400 font-bold' : 'border-outline-variant/40 hover:bg-surface-container'}`}>
              drop {modelInfo(m).label}
            </button>
          ))}
          {simulatedDisabledModel && (
            <button onClick={resetFailureState} className="px-2.5 py-1 rounded border border-primary/50 text-primary font-bold flex items-center gap-1"><RotateCcw className="w-3 h-3" /> restore</button>
          )}
        </div>
        {simulatedDisabledModel && (
          <div className="mt-2">Re-normalised weights: {summary.weights?.filter(w => w.weight > 0).map(w => `${modelInfo(w.model_id).label} ${(w.weight * 100).toFixed(0)}%`).join(' · ')}</div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={card}>
          <div className="font-bold text-sm font-sans mb-2">Recent live fetches</div>
          {datasets.length === 0 ? <div className="text-on-surface-variant">None yet.</div> : datasets.map(d => (
            <div key={d.dataset_id} className="py-1 border-t border-outline-variant/20 first:border-0">
              <div className="flex justify-between gap-2"><span className="break-all">{d.dataset_id}</span><span>{d.records} rec</span></div>
              <div className="text-[10px] text-on-surface-variant">{d.badge} · received {fmtTime(d.metadata?.fetched_at || d.ingested_at)}{d.metadata?.missing && Object.keys(d.metadata.missing).length ? ` · missing ${Object.keys(d.metadata.missing).join(', ')}` : ''}</div>
            </div>
          ))}
        </div>
        <div className={card}>
          <div className="font-bold text-sm font-sans mb-2">Operational events (audit trail)</div>
          {eventsNote && <div className="text-on-surface-variant">{eventsNote}</div>}
          {events.map(e => (
            <div key={e.seq} className="py-1 border-t border-outline-variant/20 first:border-0">
              <span className="text-on-surface-variant">{fmtTime(e.timestamp)}</span> · <strong>{e.action}</strong> · {e.result} · {e.actor}
              {e.reason && <div className="text-[10px] text-rose-700 dark:text-rose-400 break-all">{e.reason}</div>}
            </div>
          ))}
          {!eventsNote && events.length === 0 && <div className="text-on-surface-variant">No ingest / fetch / verification events yet.</div>}
        </div>
      </div>
    </div>
  );
};
