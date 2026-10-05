# VARUNA — Adaptive Forecast Intelligence Platform

**SIH26081 · Hybrid AI–NWP Multi-Model Forecast Blending · MoES / NCMRWF · Theme: Disaster Management**

> *Don't ask which weather model is best. Ask which model should be trusted — where, when, and by how much.*

VARUNA is a decision-support layer that sits **on top of** existing forecasting systems (NCUM, GFS, WRF and AI weather models). For every region, lead time and weather regime it decides how much to trust each model, blends them, quantifies disagreement and uncertainty, explains the result in plain language, and verifies itself against observations.

> **Status: research prototype, India-first.** Verification truth is **IMD gridded observations** (rainfall 0.25°, Tmax; ERA5 only as fallback / for wind). NCMRWF / IMD forecast files (NCUM, NEPS, IMD GFS/WRF) enter through a drop folder or upload and take priority; global models (GFS, ECMWF IFS/AIFS, UK Met Office UM, DWD ICON) extracted over Indian subdivisions are a labelled reference lane. A *synthetic* demo is used only when nothing real is stored. Nothing here is operational IMD/NCMRWF guidance. See [`AUDIT_NOTES.md`](./AUDIT_NOTES.md) and [`DATA_SOURCES.md`](./DATA_SOURCES.md).

---

## Repository layout

```
VARUNA/
├── backend/                 FastAPI service, 14-stage forecast pipeline, ML/stacking engines, tests  → backend/README.md
├── frontend/                React 18 + Vite + Tailwind control-room UI (light & dark)               → frontend/README.md
├── data/synthetic/varuna_synth/   Synthetic multi-model dataset generator (CSV / Parquet / NetCDF / Zarr)
├── varuna_feel3/varuna/varuna_ingest/  Stand-alone format adapters (tabular / gridded / GRIB2 / API JSON)
├── scripts/                 verify_real_data.py (real-data acceptance test), demo_video/ (judge-video recorder + voice-over)
├── varuna_forecast_intelligence_platform/   UI design mock-ups (reference only)
├── AUDIT_NOTES.md           Audit findings, fixes, benchmark results, roadmap
├── DATA_SOURCES.md          India-first data tiers: IMD gridded, NCMRWF drop folder, IMD API, global reference
├── Dockerfile · render.yaml Deployment (API)
└── requirements.txt         → backend/requirements.txt
```

## How the pipeline works

```
 NCUM ─┐
 GFS  ─┤   1 Ingest → 2 QC → 3 Harmonise units/ids → 4 Context (region, season, lead, regime)
 WRF  ─┤   5 Historical skill (DB or bootstrap prior) → 6 Raw disagreement
 AI   ─┘   7 Trust weights  ── ADAPTIVE_ML (GBDT error model + softmax)
                             ── ADAPTIVE_RELIABILITY (skill × recent error × regime vulnerability)
                             ── BIAS_CORRECTED_STACK (conditional bias removal + NNLS weights)
           8 Weighted disagreement → 9 Fusion (+ simple-average & static-blend baselines)
           10 Uncertainty & confidence → 11 Extreme signal (IMD thresholds) → 12 XAI briefing
           13 Forecast-intelligence package → 14 Verification & skill feedback (when observations exist)
```

Guarantees enforced in code: weights are non-negative and sum to 1; missing models are excluded and the rest re-normalised; a single remaining model is flagged `DEGRADED_SINGLE_SOURCE`; an LLM (optional) only rephrases computed facts and never changes numbers.

## Benchmark (synthetic, leak-free chronological split)

500 synthetic days, 60 % train / 15 % validation / 25 % test (125 unseen days). MAE in mm, default seed 101:

| Method | MAE | vs simple average |
|---|---|---|
| Best single model (NCUM) | 7.44 | −45 % |
| Simple multi-model average | 5.12 | baseline |
| Adaptive reliability (heuristic) | 5.03 | +1.8 % |
| Adaptive ML meta-model | 5.07 | +1.0 % |
| **Bias-corrected conditional stacking** | **4.97** | **+2.9 %** |

Across five seeds stacking improves on the simple average every time (+2.9 % to +18.7 %). Numbers are produced live by `GET /api/verification/compare`; earlier "+4.3 %" / "+38 %" figures were not reproducible and were removed (details in `AUDIT_NOTES.md`).

## Quick start

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # SQLite by default; never commit .env
uvicorn app.main:app --reload --port 8000               # Swagger: http://localhost:8000/api/docs
pytest tests -q                                         # 78 tests, isolated SQLite DB
```

**Frontend** (Node 18+):

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000  (proxies /api → http://127.0.0.1:8000)
npm run build          # type-check + production bundle in dist/
```

Demo accounts (seeded on first start, password `varuna2026`): `forecaster@`, `ops@`, `analyst@`, `admin@`, `auditor@ncmrwf.gov.in`. There is no public sign-up; administrators create accounts (Governance → Users). **First real-data steps:** sign in as `ops@…` → *Data sources* → read an **IMD gridded** value, **Fetch** global models, **Run backfill** (truth = IMD gridded), and scan the **NCMRWF drop folder** once files are delivered. If the API is unreachable the UI starts an *offline demo session*; wrong passwords are always rejected.

**Check it on real data** (backend running, internet access to imdpune.gov.in and open-meteo.com):

```bash
python scripts/verify_real_data.py --days 60     # PASS / WARN / FAIL per step; must end with 0 failed
```

**Hosting:** the frontend deploys to Vercel (`frontend/vercel.json`, which proxies `/api` to Render); see `frontend/README.md`.

**Docker / Render:** `docker build -t varuna . && docker run -p 8000:8000 --env-file backend/.env varuna`. `render.yaml` deploys the API with a managed PostgreSQL database.

## Data sources (India-first — details in [`DATA_SOURCES.md`](./DATA_SOURCES.md))

| Tier | Source | Status |
|---|---|---|
| India · truth | IMD gridded daily rainfall (0.25°) & Tmax (IMD Pune) | **Connected** (public download, cached; `.grd` upload if the server is offline) |
| India · forecasts | NCMRWF NCUM-G/R, NEPS; IMD GFS/WRF | **Drop-folder / upload ingest ready** (`NCMRWF_DROP_DIR`, `POST /api/india/ncmrwf/scan`); needs institutional access |
| India · observations & warnings | IMD API (station obs, district rainfall, district warnings, city forecasts) | **Adapter ready**, dormant until IMD grants access (`IMD_API_ENABLED`) |
| India · history / satellite | IMDAA reanalysis, ISRO MOSDAC INSAT-3D | Manual download + upload |
| Global reference | GFS, ECMWF IFS, ECMWF AIFS, UK Met Office UM, DWD ICON over India (Open-Meteo) | **Connected**, labelled "global model", never "NCMRWF/IMD" |
| Demo | Synthetic scenarios & benchmark | Labelled `SYNTHETIC_*` |

## Roles (enforced on the API by a permission matrix — `GET /api/auth/roles`)

| Role | Home page | Can |
|---|---|---|
| FORECASTER | Control room | view forecasts & explanations, record observations (stage 14), notifications |
| OPERATIONS | Data sources | + fetch live data, backfill, upload files |
| ANALYST | Verification centre | + update skill memory, run experiments, **propose** scientific changes |
| ADMIN | Governance | manage users, **approve/reject** proposals, read audit — cannot edit forecasts, skill or audit rows |
| AUDITOR | Audit trail | read-only: audit trail (hash-chain verification), configuration, evidence |

Each account has exactly one role, fixed at sign-in. There is no role switcher in the UI: a person who needs another role gets a separate account from an administrator, and the API checks every request against the account's own permissions.

Every sign-in, denial, ingest, fetch, verification, skill update, user change and approval is written to an append-only, hash-chained audit log.

## Further reading

- [`AUDIT_NOTES.md`](./AUDIT_NOTES.md) — defects fixed, security notes, clean-up list, roadmap
- [`DATA_SOURCES.md`](./DATA_SOURCES.md) — connecting live, institutional and file data; honest limits
- [`backend/README.md`](./backend/README.md) — API, configuration, pipeline internals
- [`frontend/README.md`](./frontend/README.md) — UI structure, theming rules
- [`scripts/demo_video/README.md`](./scripts/demo_video/README.md) — recording the 3-minute judge video (five SIH26081 outcomes) and its voice-over
- [`VARUNA_SCIENTIFIC_VALIDATION_REPORT.md`](./VARUNA_SCIENTIFIC_VALIDATION_REPORT.md), [`FRONTEND_CONTROL_ROOM_CONTRACT.md`](./FRONTEND_CONTROL_ROOM_CONTRACT.md) — earlier design documents (historical; numbers superseded by the live benchmark)

MIT License · Smart India Hackathon 2026 · Prototype decision support — does not replace official IMD warnings.
