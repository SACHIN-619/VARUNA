import React, { useEffect, useState } from 'react';
import { useVaruna } from '../context/VarunaContext';
import {
  getIndiaSources, IndiaCatalog, imdGridFetch, imdGridUpload, imdObservation, liveBackfill, liveDatasets, liveFetch, ncmrwfScan,
} from '../services/platform';
import { fmtTime } from '../utils/models';
import { Download, History, Lock, RefreshCw, ExternalLink, CheckCircle2, AlertTriangle, Upload, FolderSync, MapPin, Globe2 } from 'lucide-react';

const card = 'bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30';
const input = 'px-2 py-1 rounded border border-outline-variant/40 bg-surface text-on-surface';
const STATUS: Record<string, string> = {
  AVAILABLE: 'text-emerald-700 dark:text-emerald-400', CONFIGURED: 'text-emerald-700 dark:text-emerald-400',
  NOT_CONFIGURED: 'text-amber-700 dark:text-amber-400', UPLOAD_ONLY: 'text-amber-700 dark:text-amber-400',
  MANUAL_UPLOAD: 'text-on-surface-variant',
};
const iso = (d: Date) => d.toISOString().slice(0, 10);

/**
 * Data sources, India-first (SIH26081 is for MoES / NCMRWF):
 *   1. Indian sources — IMD gridded truth, IMD API, NCMRWF product drop, IMDAA, MOSDAC
 *   2. Global public models extracted over India (reference lane / gap-filler)
 *   3. Verified skill (backfill) — IMD gridded truth by default, ERA5 fallback
 */
export const LiveDataPage: React.FC = () => {
  const { regionId, subdivisions, can, refreshData, refreshNotifications, setDataSourcePref, dataSourcePref, variable } = useVaruna();
  const [cat, setCat] = useState<IndiaCatalog | null>(null);
  const [catErr, setCatErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<Record<string, any>>({});
  const [vars, setVars] = useState<string[]>(['rainfall', 'temperature', 'wind_speed']);
  const [backfillVar, setBackfillVar] = useState('rainfall');
  const [truth, setTruth] = useState('AUTO');
  const [days, setDays] = useState(60);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [gridDay, setGridDay] = useState(iso(new Date(Date.now() - 3 * 864e5)));
  const [upFile, setUpFile] = useState<File | null>(null);
  const [upVar, setUpVar] = useState('rainfall');
  const [upKind, setUpKind] = useState('realtime');
  const [upKey, setUpKey] = useState(iso(new Date(Date.now() - 3 * 864e5)));
  const region = subdivisions.find(s => s.id === regionId);

  const loadDatasets = () => liveDatasets().then(setDatasets).catch(() => setDatasets([]));
  const loadCat = () => getIndiaSources().then(setCat).catch(e => setCatErr(e.message));
  useEffect(() => { loadCat(); loadDatasets(); }, []);

  const act = async (key: string, fn: () => Promise<any>, after?: () => void) => {
    setBusy(key); setMsg(m => ({ ...m, [key]: null }));
    try { const r = await fn(); setMsg(m => ({ ...m, [key]: { ok: true, data: r } })); after && after(); }
    catch (e: any) { setMsg(m => ({ ...m, [key]: { ok: false, error: e.message } })); }
    finally { setBusy(null); }
  };
  const Err: React.FC<{ k: string }> = ({ k }) => msg[k] && !msg[k].ok
    ? <div className="mt-2 text-error flex items-start gap-1"><AlertTriangle className="w-3.5 h-3.5 shrink-0" />{msg[k].error}</div> : null;
  const src = (id: string) => cat?.india_primary.find(s => s.id === id);
  const StatusChip: React.FC<{ id: string }> = ({ id }) => {
    const s = src(id);
    return s ? <span className={`font-bold ${STATUS[s.status] || ''}`}>{s.status.replace('_', ' ')}</span> : null;
  };

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-4 font-mono text-xs text-on-surface">
      <div>
        <h1 className="text-lg font-bold font-sans">Data sources · India-first</h1>
        <p className="text-on-surface-variant max-w-3xl mt-1 font-sans text-sm">
          VARUNA blends forecasts for Indian subdivisions. Indian sources come first: NCMRWF/IMD forecast products, IMD observations,
          and IMD gridded data as verification truth. Global public models (extracted over India only) are a reference lane and
          gap-filler, never labelled as NCMRWF/IMD output. Region: <strong className="text-on-surface">{region?.name}</strong>.
        </p>
      </div>
      {catErr && <div className={`${card} text-error`}>Catalogue unavailable: {catErr}</div>}

      {/* ── Tier 1: Indian sources ─────────────────────────────────────────── */}
      <div className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant">1 · Indian sources (primary)</div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className={card}>
          <div className="flex items-center justify-between gap-2 mb-1"><span className="font-bold text-sm font-sans">IMD gridded observations</span><StatusChip id="IMD_GRIDDED" /></div>
          <div className="text-on-surface-variant mb-2">IMD Pune daily rainfall (0.25°) and Tmax — the verification truth for India. Public, no login. Rainfall day = 08:30 IST → 08:30 IST.</div>
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Day</span>
              <input type="date" value={gridDay} onChange={e => setGridDay(e.target.value)} className={input} /></label>
            {can('live:fetch') && (
              <button disabled={!!busy} onClick={() => act('grid', () => imdGridFetch(regionId, variable === 'temperature' ? 'temperature' : 'rainfall', gridDay))}
                className="px-2.5 py-1 rounded bg-primary text-on-primary font-bold disabled:opacity-40 flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" /> {busy === 'grid' ? 'Reading…' : 'Read value'}
              </button>
            )}
          </div>
          {msg.grid?.ok && (() => {
            const d = msg.grid.data; const v = d.truth?.[gridDay]; const cell: any = Object.values(d.cells || {})[0] || {};
            return <div className="mt-2 p-2 rounded bg-surface-container-low">
              <div className="font-bold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />{d.variable} {gridDay}: {v ?? '—'} {d.variable === 'rainfall' ? 'mm' : '°C'}</div>
              <div className="text-[10px] text-on-surface-variant">grid cell {cell.cell_lat}, {cell.cell_lon} ({cell.resolution}) · {d.files?.join(', ')}</div>
            </div>;
          })()}
          <Err k="grid" />
          {can('data:ingest') && (
            <details className="mt-3">
              <summary className="cursor-pointer text-primary">Server can't reach imdpune.gov.in? Upload the .grd file</summary>
              <div className="mt-2 flex flex-wrap items-end gap-2">
                <select value={upVar} onChange={e => setUpVar(e.target.value)} className={input}><option value="rainfall">rainfall</option><option value="temperature">Tmax</option></select>
                <select value={upKind} onChange={e => { setUpKind(e.target.value); setUpKey(e.target.value === 'archive' ? String(new Date().getFullYear() - 1) : gridDay); }} className={input}>
                  <option value="realtime">daily (real-time)</option><option value="archive">yearly (archive)</option>
                </select>
                <input value={upKey} onChange={e => setUpKey(e.target.value)} placeholder={upKind === 'archive' ? 'YYYY' : 'YYYY-MM-DD'} className={`${input} w-28`} />
                <input type="file" accept=".grd,.GRD" onChange={e => setUpFile(e.target.files?.[0] || null)} className="text-[11px] max-w-[180px]" />
                <button disabled={!upFile || !!busy} onClick={() => upFile && act('upload', () => imdGridUpload(upFile, upVar, upKind, upKey), loadCat)}
                  className="px-2.5 py-1 rounded border border-primary/50 text-primary font-bold disabled:opacity-40 flex items-center gap-1"><Upload className="w-3.5 h-3.5" /> Upload</button>
              </div>
              <div className="text-[10px] text-on-surface-variant mt-1">Files: imdpune.gov.in → gridded / real-time data. Layout checked on upload (129×135 rain, 31×31 or 61×61 Tmax).</div>
              {msg.upload?.ok && <div className="mt-1 text-emerald-700 dark:text-emerald-400">Stored {msg.upload.data.stored_as} · {msg.upload.data.days} day(s) · sha256 {msg.upload.data.sha256.slice(0, 12)}…</div>}
              <Err k="upload" />
            </details>
          )}
        </div>

        <div className={card}>
          <div className="flex items-center justify-between gap-2 mb-1"><span className="font-bold text-sm font-sans">NCMRWF / IMD forecast files</span><StatusChip id="NCMRWF_NCUM" /></div>
          <div className="text-on-surface-variant mb-2">NCUM-G/R, NEPS (and IMD GFS / WRF) delivered under an institutional agreement. Files in the drop folder are ingested as <em>authorised operational feed</em> and take priority over global models.</div>
          <div className="text-[10px] text-on-surface-variant mb-2">{src('NCMRWF_NCUM')?.detail}</div>
          {can('data:ingest') ? (
            <button disabled={!!busy} onClick={() => act('scan', ncmrwfScan, () => { loadDatasets(); refreshData(); })}
              className="px-2.5 py-1 rounded bg-primary text-on-primary font-bold disabled:opacity-40 flex items-center gap-1">
              <FolderSync className="w-3.5 h-3.5" /> {busy === 'scan' ? 'Scanning…' : 'Scan drop folder'}
            </button>
          ) : <div className="text-on-surface-variant flex items-center gap-1"><Lock className="w-3.5 h-3.5" /> data:ingest required</div>}
          {msg.scan?.ok && (
            <div className="mt-2 space-y-0.5">{msg.scan.data.files.length === 0 ? <div className="text-on-surface-variant">No ingestible files in the folder.</div> :
              msg.scan.data.files.map((f: any) => <div key={f.file + f.sha256}><strong>{f.status}</strong> {f.file}{f.records != null ? ` · ${f.records} records` : ''}{f.error ? ` · ${f.error}` : ''}</div>)}</div>
          )}
          <Err k="scan" />
          <div className="text-[10px] text-on-surface-variant mt-2">Or use the Upload button in the top bar with provenance "authorised operational feed".</div>
        </div>

        <div className={card}>
          <div className="flex items-center justify-between gap-2 mb-1"><span className="font-bold text-sm font-sans">IMD API</span><StatusChip id="IMD_API" /></div>
          <div className="text-on-surface-variant mb-2">Station observations (last 24 h rain, temperature, wind), district rainfall, district warning colours and city forecasts from api.imd.gov.in.</div>
          <div className="text-[10px] text-on-surface-variant mb-2">{src('IMD_API')?.detail} Station for this region: {cat?.station_map?.[regionId] ? `${cat.station_map[regionId].name || ''} (${cat.station_map[regionId].station}) — verify with IMD` : 'not mapped (IMD_STATION_MAP)'}.</div>
          <button disabled={!!busy || src('IMD_API')?.status !== 'CONFIGURED'} onClick={() => act('obs', () => imdObservation(regionId))}
            className="px-2.5 py-1 rounded border border-primary/50 text-primary font-bold disabled:opacity-40">Latest observation</button>
          {msg.obs?.ok && (
            <div className="mt-2 p-2 rounded bg-surface-container-low">
              <div className="font-bold">{msg.obs.data.station} · {msg.obs.data.observed_date} {msg.obs.data.observed_time_utc} UTC</div>
              <div>24 h rain {msg.obs.data.rainfall_24h_mm ?? '—'} mm · T {msg.obs.data.temperature_c ?? '—'} °C · wind {msg.obs.data.wind_speed_ms ?? '—'} m/s</div>
            </div>
          )}
          <Err k="obs" />
          <a href="https://api.imd.gov.in/public/api_reference.html" target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-primary">API reference <ExternalLink className="w-3 h-3" /></a>
        </div>
      </div>

      {cat && (
        <div className={card}>
          <div className="font-bold text-sm font-sans mb-2">All Indian sources</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] min-w-[720px] [&_th]:px-1.5 [&_td]:px-1.5">
              <thead><tr className="text-left text-on-surface-variant"><th>source</th><th>provider</th><th>role in VARUNA</th><th>access</th><th>status</th></tr></thead>
              <tbody>{cat.india_primary.map(s => (
                <tr key={s.id} className="border-t border-outline-variant/20 align-top">
                  <td className="py-1"><a href={s.url} target="_blank" rel="noreferrer" className="text-primary">{s.name}</a></td>
                  <td>{s.provider}</td><td>{s.role}</td><td>{s.access}</td><td className={`font-bold ${STATUS[s.status] || ''}`}>{s.status.replace('_', ' ')}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <div className="text-[10px] text-on-surface-variant mt-2">{cat.attribution} Step-by-step access guide: DATA_SOURCES.md.</div>
        </div>
      )}

      {/* ── Tier 2: global reference models ───────────────────────────────── */}
      <div className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant flex items-center gap-1"><Globe2 className="w-3.5 h-3.5" /> 2 · Global public models over India (reference lane)</div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={card}>
          <div className="flex items-center gap-2 font-bold text-sm mb-2"><Download className="w-4 h-4" /> Fetch global model forecasts</div>
          <div className="text-on-surface-variant mb-2">{cat?.global_reference.note}</div>
          <div className="flex flex-wrap gap-3 mb-2">
            {[['rainfall', 'Rainfall'], ['temperature', 'Max temperature'], ['wind_speed', 'Max wind']].map(([v, l]) => (
              <label key={v} className="flex items-center gap-1"><input type="checkbox" checked={vars.includes(v)} onChange={e => setVars(e.target.checked ? [...vars, v] : vars.filter(x => x !== v))} /> {l}</label>
            ))}
          </div>
          {can('live:fetch') ? (
            <button disabled={!!busy || !vars.length || cat?.global_reference.enabled === false}
              onClick={() => act('fetch', () => liveFetch(regionId, vars), () => { loadDatasets(); if (dataSourcePref === 'demo') setDataSourcePref('auto'); refreshData(); refreshNotifications(); })}
              className="px-3 py-1.5 rounded border border-primary/50 text-primary font-bold flex items-center gap-1 disabled:opacity-40">
              <RefreshCw className={`w-3.5 h-3.5 ${busy === 'fetch' ? 'animate-spin' : ''}`} /> {busy === 'fetch' ? 'Fetching…' : 'Fetch now'}
            </button>
          ) : <div className="text-on-surface-variant flex items-center gap-1"><Lock className="w-3.5 h-3.5" /> live:fetch required</div>}
          {msg.fetch?.ok && msg.fetch.data.results.map((r: any) => (
            <div key={r.dataset_id} className="mt-2 p-2 rounded bg-surface-container-low">
              <div className="font-bold">{r.variable}: {r.records} values from {r.models_received.length} models</div>
              <div className="text-[10px] text-on-surface-variant break-all">received {fmtTime(r.fetched_at)} · sha256 {r.checksum.slice(0, 16)}… · grid {r.grid?.latitude}, {r.grid?.longitude}</div>
              {Object.keys(r.missing || {}).length > 0 && <div className="text-[10px] text-amber-700 dark:text-amber-400">Missing: {Object.keys(r.missing).join(', ')}</div>}
            </div>
          ))}
          <Err k="fetch" />
          {cat && <div className="mt-2 text-[10px] text-on-surface-variant">Models: {cat.global_reference.models.map(m => m.name).join(' · ')}. {cat.global_reference.licence}</div>}
        </div>

        {/* ── Verified skill ─────────────────────────────────────────────── */}
        <div className={card}>
          <div className="flex items-center gap-2 font-bold text-sm mb-2"><History className="w-4 h-4" /> Build verified skill (backfill)</div>
          <div className="text-on-surface-variant mb-2">What each model forecast 24 h and 48 h ahead over the last N days, compared with <strong>IMD gridded observations</strong> (rainfall, Tmax; ERA5 only for wind or if IMD is unreachable). Stores the errors, computes MAE / RMSE / bias and fits the bias-corrected blend for this region.</div>
          <div className="flex flex-wrap items-end gap-2 mb-2">
            <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Variable</span>
              <select value={backfillVar} onChange={e => setBackfillVar(e.target.value)} className={input}>
                <option value="rainfall">Rainfall</option><option value="temperature">Max temperature</option><option value="wind_speed">Max wind</option>
              </select></label>
            <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Truth</span>
              <select value={truth} onChange={e => setTruth(e.target.value)} className={input}>
                <option value="AUTO">IMD gridded (ERA5 fallback)</option><option value="IMD_GRIDDED">IMD gridded only</option><option value="ERA5">ERA5 only</option>
              </select></label>
            <label className="flex flex-col gap-0.5"><span className="text-[10px] text-on-surface-variant">Days</span>
              <input type="number" min={10} max={365} value={days} onChange={e => setDays(Number(e.target.value))} className={`${input} w-20`} /></label>
            {can('live:fetch') && (
              <button disabled={!!busy} onClick={() => act('bf', () => liveBackfill(regionId, backfillVar, days, truth), () => { loadDatasets(); refreshData(); })}
                className="px-3 py-1.5 rounded bg-primary text-on-primary font-bold disabled:opacity-40">{busy === 'bf' ? 'Running…' : 'Run backfill'}</button>
            )}
          </div>
          {msg.bf?.ok && (() => {
            const b = msg.bf.data;
            return <div className="mt-2 space-y-2">
              <div className="text-[10px]"><strong>Truth: {b.truth_name}</strong> · window {b.window[0]} → {b.window[1]} · {b.verification_rows} verification rows · {b.observations} days
                {b.truth_note && <div className="text-on-surface-variant">{b.truth_note}</div>}</div>
              {Object.entries<any>(b.leads).map(([lead, c]) => (
                <div key={lead} className="p-2 rounded bg-surface-container-low">
                  <div className="font-bold">Lead {lead} h</div>
                  <table className="w-full text-[10px] mt-1 [&_th]:px-1.5 [&_td]:px-1.5">
                    <thead><tr className="text-on-surface-variant"><th className="text-left">model</th><th className="text-right">MAE</th><th className="text-right">RMSE</th><th className="text-right">bias</th><th className="text-right">n</th></tr></thead>
                    <tbody>{Object.entries<any>(c.per_model).map(([m, s]) => (
                      <tr key={m}><td>{m}</td><td className="text-right">{s.MAE}</td><td className="text-right">{s.RMSE}</td><td className="text-right">{s.BIAS}</td><td className="text-right">{s.n}</td></tr>
                    ))}</tbody>
                  </table>
                  {c.holdout ? <div className="mt-1 text-[10px]">Hold-out ({c.holdout.train_days}/{c.holdout.test_days} days): stacking MAE <strong>{c.holdout.stacking_mae}</strong> · average {c.holdout.simple_average_mae} · best single ({c.holdout.best_single_model}) {c.holdout.best_single_model_mae}</div>
                    : <div className="text-[10px] text-on-surface-variant mt-1">{c.stacker}</div>}
                </div>
              ))}
            </div>;
          })()}
          <Err k="bf" />
        </div>
      </div>

      {cat && cat.restricted.length > 0 && (
        <div className={card}>
          <div className="font-bold text-sm font-sans mb-1">Not publicly available</div>
          {cat.restricted.map(m => <div key={m.slot} className="mt-1 flex items-start gap-1.5"><Lock className="w-3.5 h-3.5 mt-0.5 shrink-0" /><span><strong>{m.slot}</strong>: {m.how_to_get}</span></div>)}
        </div>
      )}

      <div className={card}>
        <div className="font-bold text-sm font-sans mb-2">Stored fetches (newest first)</div>
        {datasets.length === 0 ? <div className="text-on-surface-variant">Nothing fetched yet.</div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] min-w-[640px] [&_th]:px-1.5 [&_td]:px-1.5">
              <thead><tr className="text-on-surface-variant text-left"><th>dataset</th><th>type</th><th className="text-right">records</th><th>received</th><th>sha256</th><th>request</th></tr></thead>
              <tbody>{datasets.map(d => (
                <tr key={d.dataset_id} className="border-t border-outline-variant/20">
                  <td className="py-1 break-all">{d.dataset_id}</td><td>{d.badge}</td><td className="text-right">{d.records}</td>
                  <td>{fmtTime(d.metadata?.fetched_at || d.ingested_at)}</td><td>{(d.checksum || '').slice(0, 12)}…</td>
                  <td>{d.url && d.url.startsWith('http') && <a href={d.url} target="_blank" rel="noreferrer" className="text-primary inline-flex items-center gap-0.5">open <ExternalLink className="w-3 h-3" /></a>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
