# VARUNA — Engineering & Scientific Audit Notes

**Date:** 4 Oct 2026 (pass 1 + pass 2) · **Scope:** whole repository (backend, frontend, data generators, scripts, docs) · **Problem statement:** SIH26081 — Hybrid AI–NWP multi-model forecast blending (MoES / NCMRWF)

This file records what was checked, what was broken, what was changed, and what is still open. Every "fixed" item has a regression test in `backend/tests/test_audit_regressions.py` or was verified in a headless browser (light + dark, desktop + 390 px mobile).

---

## 0. Verification summary

| Check | Before | After |
|---|---|---|
| Backend tests | 40 passed | **77 passed** on SQLite **and on PostgreSQL 16 upgraded from the original schema** (11 + 15 + 11 new tests) |
| GET endpoints returning HTTP 500 | 2 (`/api/fusion/current`, `/api/extremes`) | **0 / 32** |
| Frontend type-check (`tsc --noEmit`) | clean | clean |
| Ingestion throughput (15,840-row `varuna_synth` CSV, SQLite) | ~1,570 rec/s, **33% of rows rejected**, units stored as `UNVERIFIED_UNIT` | **~11,400 rec/s**, only the unsupported `wind_direction` rows rejected, canonical units |
| Dashboard pipeline latency (warm) | 7–15 ms | 7–15 ms (unchanged); weight-map cached |
| First request after start-up | ~3.7 s (model training on demand) | model warmed in `lifespan` start-up |
| Wrong password at login | **logged in anyway** (frontend fallback) | rejected (401 → error message) |

---

## 1. Critical defects fixed (correctness / accuracy)

1. **Fused value was 0.0 for every downstream stage.** `canonical_pipeline.py` read `fusion_result["fused_forecast"]`, but fusion returns `fused_value`. Uncertainty, the exceedance probability, the extreme-event signal and the XAI briefing were all computed for 0 mm. → fixed; probability/alerts now track the real blend.
2. **Lead time never reached the models.** `ContextVector` stores `lead_time`; ML features, uncertainty lead-decay and the explanation read `lead_hours` → always 48 h. → alias added; confidence now falls with lead (0.61 → 0.52 → 0.45 for 24/48/72 h).
3. **Target leakage in the ML bootstrap.** `recent_error` was set to `0.5 × |current target error|`, so the regressor learned `error = 2 × recent_error` and ignored regime/lead/season. Weights did not change when the user changed lead time or regime. → strictly causal bootstrap (independent prior draws), stale artifacts auto-retrained via a manifest version check.
4. **Weather regime, season, strategy and forced-disagreement were silently dropped** by `scenario_generator` → the regime selector, the "Adaptive ML / Reliability" toggle and "simulate disagreement" had no effect. → all honoured.
5. **Temperature and wind re-used rainfall millimetres** (`/api/extremes` reported a 70 "°C" heat-wave; wind compared m/s against a km/h threshold). → variable-specific demo feeds, canonical m/s, IMD-aligned categories (Yellow ≥ 64.5 mm, Orange ≥ 115.6 mm, Red ≥ 204.5 mm; heat-wave ≥ 40 °C; gale ≥ 14 m/s).
6. **The ML meta-model (trained on rainfall mm) was applied to °C and m/s.** → non-rainfall variables use the adaptive-reliability engine until variable-specific models exist.
7. **`/api/forecast/intelligence` (used by the UI) ignored the database** (`db=None`), so uploaded datasets never influenced forecasts; the DB path also loaded *every* historical row with `.all()` and kept an arbitrary value per model. → DB-backed, latest issue time only, model-id aliasing.
8. **Fabricated verification numbers.** `/api/verification/summary|compare` used a hand-typed 10-row table whose "adaptive" column was entered manually (reported **79 % MAE reduction**). The UI's "+4.3 %" was also hard-coded. → both endpoints now serve the real leak-free benchmark (see §3). Benchmark-dependent badges in the UI read the measured value.
9. **Running the benchmark replaced the production model.** `benchmark_runner` fitted and saved the global `ml_trust_model` singleton. → isolated instance in a temp dir.
10. **Skill feedback loop excluded 0 mm values** from BIAS (`if r.forecast_value and r.observed_value`) and could overwrite DB skill with bootstrap priors; the skill lookup ignored `metric`, regime and season. → fixed.
11. Disagreement score was discontinuous (a "MODERATE" case could score below a "LOW" case). → continuous, monotone score with range escalation.
12. Spatial weight map used the global `np.random` state → the national map changed on every refresh. → deterministic per (region, lead, season, regime), LRU-cached.

## 2. Data pipeline / ingestion

- The project's own generator output (`varuna_synth`) was **not ingestible correctly**: `mm/day`, `degC`, `pct`, `surface_pressure`, `NCUM_SYNTHETIC`, region codes `WG/TEL/…` all fell through. Added unit, variable, model-id and region aliases (`harmonization.py`).
- Unparseable timestamps were silently replaced by *now()* → now rejected and counted.
- `int(NaN)` on blank `lead_hours` aborted the whole file → vectorised coalescing.
- Surface pressure over the Himalaya (~500–800 hPa) was flagged SUSPECT (bound was MSLP 870) → 300 hPa lower bound.
- Throughput: per-row Pydantic + `pd.to_datetime` + ORM objects replaced by a vectorised pandas normaliser and Core `executemany` inserts; SQLite runs in WAL mode. **7× faster**; with the SQLAlchemy C-extensions on a normal install it is faster still.
- `POST /api/datasets/ingest` was `async def` doing blocking CPU/DB work (froze the event loop for all users) → sync endpoint in the thread-pool.

## 3. Scientific benchmark — honest numbers & a better method

The README/UI claimed **+4.3 %** (ML 4.90 mm vs simple average 5.12 mm). The current code (unchanged original *and* fixed version) reproduces **+1.0 %** for the ML meta-model on the default seed — and the ML model is *worse* than the simple heuristic on that seed. The claim was not reproducible.

**New method added: Bias-Corrected Conditional Stacking** (`app/intelligence/stacking.py`). Standard multi-model post-processing practice: remove each model's regime/lead-conditional bias, then learn convex NNLS weights, shrunk toward the global fit for sparse cells. Results on the project's chronological benchmark (125 held-out test days each, MAE in mm):

| Seed | Simple avg | Heuristic | ML meta-model | **Stacking** |
|---|---|---|---|---|
| 101 | 5.12 | 5.03 | 5.07 | **4.97** |
| 7 | 5.61 | 5.67 | **5.33** | 5.37 |
| 42 | 5.55 | 5.35 | 5.62 | **5.02** |
| 2024 | 5.28 | 4.85 | 4.71 | **4.51** |
| 5 | 5.13 | 4.87 | 4.63 | **4.17** |

Stacking beats the simple average on every seed (+2.9 % to +18.7 %) and is best on 4/5. It is available as `strategy=BIAS_CORRECTED_STACK` on `/api/dashboard/summary` and in the benchmark/Experiments page. Tuning the softmax temperature on the 75-day validation split was tried and **rejected** (it over-fitted). All of this is synthetic data — none of it is operational verification.

## 4. Security

| Issue | Status |
|---|---|
| **`backend/.env` contains a live Neon PostgreSQL password and an LLM API key** (`gsk_…`, a *Groq* key, while the code calls the xAI endpoint) | **Not changed by me — rotate both credentials now**, remove the file from git history (`git filter-repo`/BFG) and keep only `.env.example`. `.gitignore` now ignores every `.env`. |
| Frontend login: any password succeeded when the API returned 401 (two layers of "guaranteed fallback") | Fixed — offline demo only when the API is unreachable |
| Backend login accepted `varuna2026` for any user without a hash | Removed; legacy demo users are upgraded at seed time; generic "invalid email or password" message |
| Write endpoints open to anonymous users (`/datasets/ingest`, `/jobs/ingest`, `/jobs/{id}/cancel`, `/verification/feedback-loop`, `/experiments/run`) | Now role-guarded; UI sends the JWT |
| UI role switcher let a Forecaster become ADMIN | Role switcher removed; the role is fixed to the signed-in account |
| ANALYST login saw an **empty sidebar** (`ANALYST` vs `MODEL_ANALYST`) | Normalised |
| `allow_origins=["*"]` with `allow_credentials=True` | Credentials only with an explicit origin list (`CORS_ORIGINS`) |
| Default `SECRET_KEY` in production | Start-up warning |
| **Running `pytest` locally used the DB in `backend/.env` (production Neon)** | `conftest.py` now forces an isolated SQLite test DB |

Still open: no rate limiting on `/auth/login`; demo/failure-injection endpoints are unauthenticated by design (acceptable for a demo, not for production); JWT stored in `localStorage`.

## 5. Frontend — light/dark mode & UI defects

- ~500 dark-only colour classes (`text-slate-100/200/300/400`, `text-cyan-300/400`, `bg-*-950`) were invisible or low-contrast in light mode → replaced with theme tokens (`text-on-surface`, `text-primary`, `bg-x-50 dark:bg-x-950`).
- Tailwind colours `secondary`, `error`, `inverse-primary` and the DESIGN.md type scale (`text-label-sm`, `text-data-display`, …) were **used but never defined** — e.g. white text on a missing `bg-secondary` button. Also missing: `shadow-xs`, `backdrop-blur-xs`, `rounded-xs`, `border-l-3`, `py-0.2`, `animate-fadeIn`, `focus:outline-hidden` (v4 syntax). All defined/mapped.
- `.dark` now works as a theme *island* (used by the always-dark map canvas); `color-scheme` set so native selects/scrollbars follow the theme; theme applied before first paint (no flash); default follows the OS; Settings page had a fake "Dark theme LOCKED" row → real toggle.
- Sidebar (288 px) overlapped the content (padding 256 px) and the collapse button left a gap → layout follows sidebar state; mobile drawer + hamburger; header no longer overlaps at 390 px.
- Variable selector sent `RAINFALL/TEMPERATURE/WIND` (backend expects `rainfall/temperature/wind_speed`; `WIND` is not a variable).
- Verification Centre **crashed** (`toFixed` of undefined); Trust-map allocation list showed `0,1,2,3 / NaN%`; weights defaulted with `|| 0.46` so a disabled model showed 46 %; the Control Room said "LIVE PIPELINE CONNECTED" and "DEMO MODE" at the same time; dropout simulation did nothing when the backend was live; logged-in session bar covered the landing navigation; redirects called `setState` during render.
- Hard-coded telemetry/claims replaced with data or neutral wording: "Judge Walkthrough", "v4.2-PROD", "100 % / 0 Pkts / 42 ms", "STATION OBS VERIFIED", "NCUM-G 0.04° Global convection-permitting" (NCUM-G is ~12 km), fixed cycle dates, "4/4 ONLINE", "VERIFIED" badges on synthetic feeds, fixed map percentages, the What-Changed previous-cycle numbers.
- Dashboard pages are deep-linkable (`/dashboard/<page>`, browser back/forward).

## 6. Irrelevant / duplicated content (not deleted — needs your decision)

Deleting files in your folder was not possible from this session. Recommended clean-up:

| Path | Why |
|---|---|
| `scratch.py` | Writes to a non-existent `improved_frontend/` with a hard-coded Windows path |
| `test_endpoints.py` (root) | Superseded by `backend/tests` |
| `varuna_feel3/varuna/varuna_synth/` | Byte-identical copy of `data/synthetic/varuna_synth/` |
| `data/varuna_forecast_intelligence_platform/` | Duplicate of `varuna_forecast_intelligence_platform/` (design mock-ups) |
| `frontend/HomePage_sample_design/` (~13 MB of video) | Duplicate of `frontend/public/assets/varuna/` |
| `frontend/public/assets/varuna/code.html`, `DESIGN.md`, `screen.png` | Design sources shipped as public web assets |
| `varuna_dev.db`, `backend/varuna_dev.db`, `backend/varuna_bench.db` (21 MB) | Database files in the repo (now git-ignored) |
| `data/storage/models/` (root) | Unused after path anchoring; artifacts live in `backend/data/storage/models/` |
| Old README sections 10+ | Contained pasted chat-assistant output ("Searched for 'role'…", `file:///c:/Users/...` links) — README rewritten |

`frontend/src/components/layout/SystemStatusBar.tsx` is unused since pass 2 (replaced by `ContextBar`) and can be deleted. Pass 2 rewired Model Performance, Operations, Data Health, System Health, Audit Log, Verification Centre, Why This Forecast and the Control Room to API data (see §9). Still illustrative: Regional lead-time cards, the subdivision trust map colours and the guided walkthrough text. (Extreme Events and Failure Memory were rewired in pass 4, below.)

## 7. Keeping VARUNA competitive (2025–26 landscape)

Context: ECMWF's AIFS ensemble became operational in 2025; MoES launched the 6 km **Bharat Forecast System** in May 2025 and IMD added AI-based block-level monsoon and 1 km rainfall products in 2026. Raw AI forecasts are no longer novel; **calibrated, explainable, verified blending of NWP + AI is**. Recommendations, in priority order:

1. **Real data first.** Ingest IMD gridded rainfall / IMDAA as truth and GFS (NOMADS), ECMWF open data / AIFS and BharatFS/NCUM where accessible as feeds; replace synthetic benchmark claims with real verification. The ingestion engine and alias layer are ready for this.
2. **Make stacking the default strategy once fitted on real history** (fit `BiasCorrectedStacker` on verification history per region × lead × regime); keep ML softmax as an option.
3. **Probabilistic output instead of the uncalibrated Gaussian:** EMOS / quantile regression / conformal prediction intervals; verify with **CRPS**, reliability diagrams and Brier skill score — the metrics NCMRWF/IMD reviewers expect.
4. **Spatial blending on the grid** (weights as smooth fields, not 14 polygons) + use real IMD subdivision boundaries instead of hand-drawn polygons.
5. **Impact-based guidance:** map blended rainfall to IMD colour codes per district, with lead-time-aware confidence.
6. **Operational hardening:** Alembic migrations, background worker (RQ/Celery) for ingestion, rate limiting, structured logs, CI running tests + `npm run build`.

## 8. Pass 2 — real data path, traceability, governance

**Real data path (priority).**
- `services/live_sources.py` + `/api/live/*`: GFS, ECMWF IFS, ECMWF AIFS, UK Met Office UM and DWD ICON forecasts from Open-Meteo for any subdivision centroid; previous-run forecasts vs ERA5 build a verification history (`VerificationResult`, `ModelSkill` with period `LIVE_BACKFILL_ERA5`) and fit a region-specific bias-corrected stacker (restored at start-up).
- Every fetch is a dataset with request URL, SHA-256, received time and grid point. NCUM/WRF are listed as *restricted* with how to obtain them; UM is never labelled NCUM. Guide: [`DATA_SOURCES.md`](./DATA_SOURCES.md).
- The pipeline now accepts any model set (the ML meta-model still needs the classic four and falls back with a stated reason).
- The dashboard has `source=auto|live|database|demo`; `auto` uses live data fetched in the last 36 h and labels everything else `SYNTHETIC_DEMO`.
- *Not verified against the real network from the audit sandbox* (Open-Meteo was blocked there); the parser is tested with Open-Meteo-shaped responses. Run one fetch on your machine first.

**Traceability.**
- Every run returns `stage_trace` (14 stages: status, timing, inputs, outputs, notes) and `lineage` (formula, terms and sources for the fused value, each weight, confidence, probability, margin, baselines, extreme level).
- QC states are now explicit: `ACCEPTED / WARNING / REJECTED / QUARANTINED (older than 48 h) / MISSING`.
- The UI stage trace is clickable. Stage 14 lets a forecaster record an observation or look up ERA5, and an analyst can then update skill memory.
- Any underlined number opens its explanation on hover or click.
- Skill lookup prefers verified history over seeded priors; recent error is an EMA of verified errors.
- XAI text states the actual evidence instead of fixed NCUM/WRF sentences.

**Notifications.** Snapshots are de-duplicated by input hash. Five rules are evaluated, and each records its formula, values and computation:
- fused jump ≥ max(abs, 25 %)
- alert level change
- dominant model change
- confidence change
- weight shift ≥ 15 pts

The bell shows the maths, both input sets and the issued and received times. What-if dropouts never notify.

**Roles & security.**
- Permission matrix with five roles, including a read-only AUDITOR. `require_permission` audits every denial.
- Admin-created accounts with one-time initial passwords and no public registration. Region scope is supported.
- The audit log is append-only and hash-chained. ORM updates and deletes raise, and `/api/audit/verify-chain` detects tampering; this is tested.
- Separation of duties: analysts propose, admins approve, nobody approves their own proposal, and admins cannot write scientific values.
- Each role has its own home page.
- *Open:* MFA (TOTP), per-request region-scope filtering on every read endpoint, password-change enforcement in the UI, and rate limiting.

**UI.**
- Compact navbar using icon buttons with labels.
- The filters moved into a wrapping context bar, so nothing disappears at 100–150 % zoom or 390 px (tested, no horizontal scroll).
- Upload only appears with `data:ingest`.
- Decorative pulse and ping animations were removed.
- The landing page shows Dashboard + Sign out when signed in, and the floating pill is gone.
- Fabricated numbers were removed from System Health, Operations, Data Health, Audit Log, Model Performance and the Control Room. Examples include "99.98 % uptime", "142/142 grids", "+4.0 % NCUM gain", fake audit rows and the hard-coded verification cycles.

**Security reminder.** `backend/.env` in the working copy contains a live Neon database URL and a Groq API key. It was not modified or copied. Rotate both and keep `.env` out of version control.

### Pass 3 — India-first data (SIH26081 is an Indian MoES / NCMRWF problem)

Open-Meteo was **kept but demoted** to a "global reference" lane: the problem statement asks to blend NWP, ensemble and AI models, and NCMRWF itself compares against global centres. Indian sources now come first:

- **IMD gridded truth** (`services/india_sources.py`). IMD Pune 0.25° rainfall and Tmax are downloaded and cached; endpoints and binary layout follow `imdlib` (MIT). The value is read at each subdivision centroid, falling back to the nearest valid cell. A `.grd` upload path covers servers that can't reach imdpune.gov.in. Backfill and stage 14 use IMD by default; ERA5 is used only for wind, or when IMD is unreachable, and the report says so.
  - Rainfall windows are aligned to the IMD 08:30 IST day (`IMD_RAIN_DAY_OFFSET_HOURS`). This convention is an assumption to confirm with IMD.
- **NCMRWF / IMD files.** A drop-folder scan ingests them as `AUTHORIZED_OPERATIONAL_FEED`, SHA-256 de-duplicated.
- **India-first merge.** Data: Auto takes the freshest record per model for one valid day, and an authorised Indian copy beats the global copy for the same slot (tested).
- **IMD API adapter.** Covers `current_wx`, `districtwarning` and the other endpoints in IMD's public API reference. It stays dormant until IMD grants access. The default station ids must be verified with IMD.
- **Not verified from the audit sandbox:** live calls to imdpune.gov.in and api.imd.gov.in. Parsers are tested with grids and JSON in the documented layout.

### Pass 3b — PostgreSQL (Neon) and Groq

- **Upgrade path checked against a real PostgreSQL 16 server.** I created the *original* schema first, set the session time zone to Asia/Kolkata to catch time-zone bugs, then started the current app on it.
  - All 77 tests pass and 43 of 43 GET endpoints return 200.
  - `audit_logs.entity_id` is now widened automatically (VARCHAR 50 → 120).
- **Hash chain stays stable on Neon.** Audit timestamps are stored as naive UTC, so the chain no longer depends on the server time zone.
- **Bug fixed: forecasts from one old cycle.**
  - Before: a stored issue older than 48 h was quarantined entirely, which crashed `/api/forecast/intelligence`.
  - Now: staleness is measured against the freshest input in the same run.
- **Groq (`gsk_…`) keys work without extra setup.** The endpoint switches to Groq's API automatically.
- **New LLM guard.** If a briefing contains a number that is not in the computed facts, the text is discarded and the deterministic template is used.

### Pass 4 — pages a judge could open on the live site

- **Extreme Events** was a hand-typed list. Its "70.1 mm" did not match the 67.2 mm shown on the dashboard for the same case. It now runs the pipeline for every subdivision × rainfall, heat and wind, grades the fused value against IMD categories, and lists the models above and below the threshold.
- **Model Failure & Drift** showed invented "observed patterns". It now reads `GET /api/verification/drift`: recent MAE against each model's own baseline, from stored verification rows (IMD-gridded or ERA5 backfill, stage-14 verifications). When there is no history, it says so. Test: `tests/test_trust_drift.py`.
- **Role switcher removed.** A role is fixed to its account.
- **`frontend/vercel.json`** proxies `/api` to Render and falls back to `index.html` for SPA routes.

## 9. How these notes were produced

Every source file was read; backend tests and a full GET-endpoint smoke test were run after each change; the frontend was type-checked and rendered in headless Chromium for 19 pages in light and dark mode plus a 390 px mobile viewport. The sandbox had no access to PyPI/npm, so the frontend was bundled with esbuild + the Tailwind 3.4 standalone CLI for verification. **Run `npm install && npm run build` on your machine once** to confirm with the project's own Vite toolchain.

Sources for §7: [ECMWF AIFS ensemble operational](https://www.ecmwf.int/en/about/media-centre/news/2025/ecmwfs-ensemble-ai-forecasts-become-operational) · [Bharat Forecast System launch](https://visionias.in/current-affairs/news-today/2025-05-27/environment/ministry-of-earth-science-launches-bharat-forecast-system-with-improved-6-km-grid-accuracy) · [IMD AI forecasting systems, May 2026](https://www.drishtiias.com/daily-updates/daily-news-analysis/imds-new-ai-driven-weather-forecasting-systems/print_manually) · [Post-processing AI weather forecasts (arXiv 2504.12672)](https://arxiv.org/html/2504.12672v2)
