import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import { modelInfo, fmtTime } from '../utils/models';
import { BarChart3, Info } from 'lucide-react';

const API_BASE: string = ((import.meta as any).env?.VITE_API_BASE as string) || '/api';
const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';

/**
 * Model skill from two clearly separated sources:
 *  1. Real: models verified against IMD gridded observations (ERA5 fallback) for the selected region.
 *  2. Synthetic: the chronological benchmark used to compare blending methods.
 * Nothing on this page is typed in by hand.
 */
export const ModelPerformancePage: React.FC = () => {
  const { regionId, variable, subdivisions, setActiveRoute, can } = useVaruna();
  const [live, setLive] = useState<any>(null);
  const [bench, setBench] = useState<any>(null);
  const region = subdivisions.find(s => s.id === regionId);

  useEffect(() => {
    fetch(`${API_BASE}/verification/live-skill?region_id=${regionId}&variable=${variable}`).then(r => r.ok ? r.json() : null).then(setLive).catch(() => setLive(null));
  }, [regionId, variable]);
  useEffect(() => {
    fetch(`${API_BASE}/verification/compare`).then(r => r.ok ? r.json() : null).then(setBench).catch(() => setBench(null));
  }, []);

  const leads = Object.keys(live?.leads || {}).sort((a, b) => Number(a) - Number(b));
  const models = Array.from(new Set(leads.flatMap(l => Object.keys(live.leads[l]))));
  const maxMae = Math.max(1, ...leads.flatMap(l => Object.values<any>(live.leads[l]).map(s => s.MAE || 0)));

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 font-mono text-xs text-on-surface">
      <div>
        <h1 className="text-lg font-bold font-sans flex items-center gap-2"><BarChart3 className="w-5 h-5" /> Model performance & skill</h1>
        <p className="text-on-surface-variant font-sans text-sm mt-1 max-w-3xl">
          Real skill of the public models for {region?.name || regionId} ({variable}), measured against {live?.reference || "IMD gridded observations (ERA5 fallback)"}, and — separately — the synthetic benchmark used to compare blending methods.
        </p>
      </div>

      <div className={card}>
        <div className="font-bold text-sm font-sans mb-2">Verified skill · {region?.name}</div>
        {leads.length === 0 ? (
          <div className="text-on-surface-variant flex items-start gap-1.5"><Info className="w-4 h-4 shrink-0" />
            <span>No verified history yet for this region and variable. {can('live:fetch')
              ? <button onClick={() => setActiveRoute('live-data')} className="text-primary underline">Run a backfill in Data sources</button>
              : 'Ask an operations officer or analyst to run a backfill in Data sources.'}</span>
          </div>
        ) : (
          <>
            <div className="text-[10px] text-on-surface-variant mb-2">Updated {fmtTime(live.updated_at)} · {live.reference} · small samples: indicative, not a published verification.</div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {models.map(m => {
                const info = modelInfo(m);
                return (
                  <div key={m} className="p-3 rounded-lg bg-surface-container-low" style={{ borderLeft: `3px solid ${info.hex}` }}>
                    <div className="font-bold">{info.label}</div>
                    <div className="text-[10px] text-on-surface-variant mb-2">{info.role}</div>
                    {leads.map(l => {
                      const s = live.leads[l][m];
                      if (!s) return null;
                      return (
                        <div key={l} className="mb-1.5">
                          <div className="flex justify-between gap-2"><span className="whitespace-nowrap shrink-0">+{l} h</span><span className="text-right">MAE {s.MAE?.toFixed(2)} · RMSE {s.RMSE?.toFixed(2)} · bias {s.BIAS > 0 ? '+' : ''}{s.BIAS?.toFixed(2)} · n {s.n}</span></div>
                          <div className="h-1.5 rounded-full bg-surface-container-high overflow-hidden"><div className="h-full rounded-full" style={{ width: `${(100 * (s.MAE || 0)) / maxMae}%`, background: info.hex }} /></div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      <div className={card}>
        <div className="font-bold text-sm font-sans mb-1">Blending methods on the synthetic chronological benchmark</div>
        <div className="text-[10px] text-on-surface-variant mb-2">{bench ? `${bench.sample_size} unseen test days · ${bench.evaluation_window} · ${bench.data_provenance}` : 'Benchmark unavailable (backend offline).'} Synthetic: shows method behaviour, not operational skill.</div>
        {bench?.methods && (
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] [&_th]:px-1.5 [&_td]:px-1.5 min-w-[520px]">
              <thead><tr className="text-left text-on-surface-variant"><th>method</th><th className="text-right">MAE</th><th className="text-right">RMSE</th><th className="text-right">bias</th></tr></thead>
              <tbody>{[...bench.methods].sort((a: any, b: any) => a.mae - b.mae).map((m: any) => (
                <tr key={m.method} className={`border-t border-outline-variant/20 ${m.method === bench.best_method ? 'font-bold text-primary' : ''}`}>
                  <td className="py-0.5">{m.method}</td><td className="text-right">{m.mae}</td><td className="text-right">{m.rmse}</td><td className="text-right">{m.bias}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
