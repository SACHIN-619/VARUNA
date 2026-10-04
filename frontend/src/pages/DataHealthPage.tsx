import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { authHeader } from '../services/auth';
import { modelInfo, fmtTime, PROVENANCE_LABEL } from '../utils/models';

const API_BASE: string = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';
const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';
const STATE: Record<string, string> = {
  ACCEPTED: 'text-emerald-700 dark:text-emerald-400', WARNING: 'text-amber-700 dark:text-amber-400',
  REJECTED: 'text-rose-700 dark:text-rose-400', QUARANTINED: 'text-purple-700 dark:text-purple-400', MISSING: 'text-on-surface-variant',
};

/** Data quality for the current run plus every registered dataset — all values come from the API. */
export const DataHealthPage: React.FC = () => {
  const { summary } = useVaruna();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetch(`${API_BASE}/datasets`, { headers: authHeader() }).then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => setDatasets(Array.isArray(d) ? d : d.datasets || [])).catch(e => setErr(String(e)));
  }, []);
  const trace = (summary.stage_trace || []).filter(t => ['INGEST', 'QC', 'HARMONIZE'].includes(t.key));
  const qc = summary.qc_state || {};
  const counts = Object.values(qc).reduce<Record<string, number>>((a, s) => ({ ...a, [s]: (a[s] || 0) + 1 }), {});

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 font-mono text-xs text-on-surface">
      <div>
        <h1 className="text-lg font-bold font-sans">Data health</h1>
        <p className="text-on-surface-variant font-sans text-sm mt-1 max-w-3xl">
          Quality-control result for the run on screen, and the registry of every dataset VARUNA holds (NCMRWF/IMD files, IMD gridded truth, global model fetches, ERA5 fallback).
        </p>
      </div>

      <div className={card}>
        <div className="font-bold text-sm mb-2">QC of the current run · {Object.entries(counts).map(([k, v]) => `${v} ${k.toLowerCase()}`).join(' · ') || 'no trace (offline)'}</div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 min-w-[560px]">
            <thead><tr className="text-left text-on-surface-variant"><th>model</th><th className="text-right">value</th><th>state</th><th>flags</th><th>source</th><th>issued</th></tr></thead>
            <tbody>{Object.keys(summary.model_forecasts || {}).map(m => (
              <tr key={m} className="border-t border-outline-variant/20">
                <td className="py-1">{modelInfo(m, summary.source_meta?.[m]).label}</td>
                <td className="text-right">{(summary.model_forecasts as any)[m] ?? '—'} {summary.unit}</td>
                <td className={`font-bold ${STATE[qc[m]] || ''}`}>{qc[m] || '—'}</td>
                <td>{(summary.qc_flags?.[m] || []).join(', ') || '—'}</td>
                <td className="break-all">{summary.source_meta?.[m]?.source || 'synthetic scenario'}</td>
                <td>{fmtTime(summary.source_meta?.[m]?.issue_time)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div className="text-[10px] text-on-surface-variant mt-2">{trace.find(t => t.key === 'QC')?.notes}</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {trace.map(t => (
          <div key={t.key} className={card}>
            <div className="font-bold">{t.stage}. {t.name} · <span className={t.status === 'PASS' ? 'text-emerald-700 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-400'}>{t.status}</span></div>
            <div className="text-[10px] text-on-surface-variant mt-1">{t.duration_ms.toFixed(2)} ms · {t.notes}</div>
          </div>
        ))}
      </div>

      <div className={card}>
        <div className="font-bold text-sm mb-2">Dataset registry ({datasets.length})</div>
        {err && <div className="text-error">{err}</div>}
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 min-w-[720px]">
            <thead><tr className="text-left text-on-surface-variant"><th>dataset</th><th>type</th><th>source</th><th className="text-right">records</th><th>coverage</th><th>ingested</th><th>sha256</th><th>status</th></tr></thead>
            <tbody>{datasets.map(d => (
              <tr key={d.dataset_id} className="border-t border-outline-variant/20">
                <td className="py-1 break-all">{d.dataset_id}</td>
                <td>{PROVENANCE_LABEL[d.provenance_badge] || d.provenance_badge}</td>
                <td>{d.source}</td><td className="text-right">{d.record_count}</td>
                <td>{d.temporal_coverage?.start?.slice(0, 10) || '—'} → {d.temporal_coverage?.end?.slice(0, 10) || '—'}</td>
                <td>{fmtTime(d.ingestion_timestamp)}</td><td>{d.checksum ? d.checksum.slice(0, 10) + '…' : '—'}</td><td>{d.status}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
