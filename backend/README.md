# VARUNA Backend

FastAPI service that runs the 14-stage multi-model blending pipeline, stores datasets and verification history, and serves the control-room UI.

## Run

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: `http://localhost:8000/api/docs` · ReDoc: `/api/redoc` · liveness `/api/health` · readiness `/api/ready`
- On start-up the schema is created, demo users/regions/models/datasets are seeded, and the ML meta-model is loaded (or retrained if the saved artifact is missing or stale).
- Relative paths in `.env` (`sqlite:///./varuna_dev.db`, `./data/storage/...`) are resolved against **this `backend/` folder**, whatever directory you start from.

## PostgreSQL / Neon

`init_db()` creates new tables, adds new columns and widens changed ones on an existing database (no data loss), so an older Neon schema upgrades on first start. The suite was run against PostgreSQL 16 starting from the **original** schema with the session time zone set to Asia/Kolkata: 77/77 pass, all 43 parameter-free GET endpoints return 200, audit chain intact. Audit timestamps are stored as naive UTC so the hash chain does not depend on the server time zone.

```bash
VARUNA_TEST_DATABASE_URL="postgresql://user:pass@host/dbname?sslmode=require" pytest tests -q   # use a *separate* test database, never production
```

## Tests

```bash
pytest tests -q          # 77 tests
```

`tests/conftest.py` always points the suite at an isolated SQLite file (`varuna_test.db`). Set `VARUNA_TEST_DATABASE_URL` to test against another database deliberately — the `DATABASE_URL` in `.env` is never used by tests.

## Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./varuna_dev.db` | PostgreSQL/Neon: `postgresql://user:pass@host/db?sslmode=require` (psycopg2 or psycopg 3 auto-detected) |
| `SECRET_KEY` | dev default | **Set in production** (a warning is logged otherwise) |
| `CORS_ORIGINS` | `["*"]` | JSON list; use explicit origins in production |
| `ML_MODEL_PATH` | `./data/storage/models` | GBDT artifacts + `artifact_manifest.json` |
| `DATA_CHUNK_SIZE` | `10000` | Rows per ingestion chunk |
| `ENABLE_GROK`, `GROK_API_KEY`, `GROK_MODEL`, `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS` | off | Optional briefing LLM; any OpenAI-compatible endpoint. A Groq key (`gsk_…`) switches the endpoint to `https://api.groq.com/openai/v1` automatically (model `GROQ_MODEL`, default `llama-3.3-70b-versatile` — check Groq's current model list). The LLM only rephrases: any number not present in the computed facts makes VARUNA discard the text and use the deterministic template. Cached per fact-set |
| `AIR_GAPPED_MODE` | `false` | Blocks all outbound calls (LLM and live data) |
| `IMD_API_ENABLED`, `IMD_API_BASE_URL`, `IMD_API_KEY`, `IMD_API_KEY_HEADER`, `IMD_STATION_MAP` | off | IMD API adapter (after IMD grants access) |
| `IMD_RAIN_DAY_OFFSET_HOURS` | `9` | Model hours aggregated on the IMD 08:30 IST rainfall day |
| `NCMRWF_DROP_DIR` | empty | Folder where NCMRWF / IMD product files are delivered |
| `LIVE_DATA_ENABLED`, `OPEN_METEO_*`, `LIVE_HTTP_TIMEOUT_SECONDS` | on | Global public models over India; see `DATA_SOURCES.md` |

Never commit `.env`. If a real database password or API key was ever committed, rotate it.

## Code map

```
app/
├── main.py                  App factory, CORS, start-up (seed + model warm-up), canonical aliases
├── core/                    config (path anchoring), database (SQLite WAL pragmas), JWT, RBAC dependencies
├── api/                     Routers: auth, dashboard, forecasts, fusion, verification, datasets, jobs,
│                            experiments, observations, regions, extremes, what-changed, models, demo, health
├── services/
│   ├── canonical_pipeline.py   The 14 stages (QC → context → skill → trust → fusion → uncertainty → extremes → XAI → verification)
│   ├── forecast_run_service.py ForecastIntelligencePackage contract (DB-backed: latest issue per model)
│   ├── ingestion.py            Chunked, vectorised ingestion (CSV/JSON/JSONL/GeoJSON/Parquet/NetCDF/ZIP)
│   ├── harmonization.py        Units, variable / model-id / region-code aliases, physical bounds
│   ├── data_pipeline.py        Verification records + closed-loop skill update
│   ├── india_sources.py        IMD gridded (download/parse/cache/upload), IMD API adapter, NCMRWF drop-folder ingest
│   ├── live_sources.py         Global models over India (Open-Meteo); backfill vs IMD gridded (ERA5 fallback); stacker refit
│   ├── notification_service.py Forecast snapshots + change rules (maths recorded)
│   ├── audit_service.py        Append-only hash-chained audit writer + chain verifier
│   └── llm_provider.py         Template / OpenAI-compatible briefing provider (cached)
├── intelligence/
│   ├── ml_trust_model.py       GBDT error regressors + softmax weights (causal bootstrap prior)
│   ├── trust_model.py          Adaptive reliability weights (heuristic baseline)
│   ├── stacking.py             Bias-corrected conditional stacking (best method on the benchmark)
│   ├── disagreement.py, uncertainty.py, explainability.py, failure_memory.py, context_engine.py
│   └── spatial_weight_map.py   14-subdivision GeoJSON trust map (deterministic, cached, HYBRID strategy)
├── experiments/benchmark_runner.py  Leak-free chronological benchmark (isolated model instance)
├── demo/                    Synthetic scenarios + scenario generator (region/lead/regime/variable aware)
├── models/ · schemas/       SQLAlchemy ORM · Pydantic contracts
└── verification/            MAE/RMSE/bias/correlation, POD/FAR/CSI, Brier
```

## Key endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/dashboard/summary?region_id&variable&lead_hours&weather_regime&season&strategy&disabled_model` | Everything the control room needs. `strategy` = `ADAPTIVE_ML` · `ADAPTIVE_RELIABILITY` · `BIAS_CORRECTED_STACK` |
| `GET /api/forecast/intelligence` | Canonical ForecastIntelligencePackage (uses ingested DB data when present) |
| `GET /api/fusion/weight-map` | GeoJSON trust map for 14 subdivisions |
| `GET /api/fusion/trace` · `/api/fusion/explanation` | Provenance trace · "Why this forecast?" |
| `GET /api/what-changed` | Diff against the previous cycle for the same valid time |
| `GET /api/extremes` | Rain / heat / wind signals with IMD colour levels |
| `GET /api/verification/compare` · `/summary` · `/experiment` | Benchmark table (single source of truth for UI metrics) |
| `GET /api/dashboard/summary?…&source=auto\|live\|database\|demo` | Also returns `source_mode`, `stage_trace` (14 stages), `lineage` (formula + sources per number), `qc_state`, `notification_id` |
| `GET /api/india/sources` | Tiered catalogue: India primary → global reference → synthetic |
| `POST /api/india/imd-grid/fetch` · `POST /api/india/imd-grid/upload` | IMD gridded rainfall / Tmax at a region (download or uploaded `.grd`) |
| `POST /api/india/ncmrwf/scan` | Ingest new NCMRWF / IMD files from `NCMRWF_DROP_DIR` as authorised feed |
| `GET /api/india/imd/observation` · `/imd/district-warning` | IMD API adapter (dormant until `IMD_API_ENABLED=true`) |
| `GET /api/live/sources` · `POST /api/live/fetch` · `POST /api/live/backfill` (`truth_source=AUTO\|IMD_GRIDDED\|ERA5`) · `GET /api/live/datasets` | Global models over India + verified skill (`live:fetch`) |
| `POST /api/verification/verify-run` | Stage 14 on demand: manual observation or ERA5 (`verification:run`) |
| `GET /api/verification/live-skill` · `/records` | Verified skill per model/lead · latest verification rows |
| `GET /api/notifications` · `/{id}` · `POST /{id}/read` · `/read-all` | Forecast-change notifications with rule maths |
| `GET /api/audit/events` · `/verify-chain` | Audit trail (`audit:view`) |
| `GET/POST /api/governance/proposals` · `/{id}/approve` · `/reject` · `GET /config` | Propose → approve (separation of duties) |
| `GET/POST /api/auth/users` · `PATCH /users/{id}` · `GET /auth/roles` · `POST /auth/change-password` | Admin-created accounts, permission matrix |
| `POST /api/datasets/ingest` | Upload a dataset (`data:ingest`) |
| `POST /api/verification/feedback-loop` | Recompute model skill from verification history (`skill:update`) |
| `POST /api/auth/login` | OAuth2 password form → JWT (24 h) |
| `POST /api/demo/inject-failure` | Demo: bias / dropout / forced disagreement / reset |

Full list (55 operations) in Swagger.

## Units & conventions

Canonical units: rainfall **mm** (24 h), temperature **°C**, wind **m/s**, humidity **%**, pressure **hPa**. Model slots: `NCUM`, `GFS`, `WRF`, `AI_WEATHER`, plus live `ECMWF_IFS`, `UKMO_UM`, `ICON` (aliases such as `NCUM_SYNTHETIC`, `GFS_0P25`, `AIFS`, `GRAPHCAST`, `ecmwf_ifs025` are mapped on ingestion). QC states: ACCEPTED · WARNING · REJECTED · QUARANTINED (> 48 h old) · MISSING. Exceedance "probabilities" are an uncalibrated Gaussian indicator (`is_calibrated_probability: false`).

## Performance (measured in the audit)

- Dashboard pipeline: ~7–15 ms per request (warm); weight map cached after first call (~25 ms cold).
- Ingestion: ~11,000 records/s on SQLite for the 15,840-row `varuna_synth` CSV (≈7× the previous engine).
- First request no longer pays model training (warm-up in start-up).
