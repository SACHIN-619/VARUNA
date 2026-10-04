# Connecting real data to VARUNA (India-first)

SIH26081 is an Indian operational problem (MoES / NCMRWF): blend forecasts for Indian regions, verify them against Indian observations, and give guidance against IMD thresholds. VARUNA therefore uses three source tiers, in this order:

| Tier | What | Why |
|---|---|---|
| **1 · India primary** | NCMRWF / IMD forecast products, IMD observations, IMD gridded data as truth, IMDAA, MOSDAC | The models and observations the problem statement is about |
| **2 · Global reference** | GFS, ECMWF IFS, ECMWF AIFS, UK Met Office UM, DWD ICON via Open-Meteo, **extracted over Indian subdivisions only** | Extra ensemble members and a gap-filler while Indian feeds are being arranged; NCMRWF itself compares against these centres |
| **3 · Synthetic demo** | Generated scenarios | Only when nothing real is stored; always labelled |

The control room's **Data: Auto (India-first)** mode merges tiers 1 and 2. For one valid day it takes the freshest record per model from the last 36 h. If an authorised Indian copy and a global copy exist for the same slot, the Indian copy wins (for example, a GFS file delivered by IMD/NCMRWF beats the public GFS). The badge then reads **NCMRWF/IMD + GLOBAL MODELS**.

## Tier 1 — Indian sources

### IMD gridded observations (connected, no login)

IMD Pune publishes daily gridded rainfall (0.25°) and maximum temperature: yearly archive files (Tmax at 1°) and daily real-time files (Tmax at 0.5°). VARUNA downloads them directly, caches them, and reads the value at each subdivision centroid. If the centroid cell is sea or missing, it uses the nearest valid cell within 2 cells. Endpoints and binary layout follow the open-source [`imdlib`](https://imdlib.readthedocs.io/en/latest/Usage.html) package (MIT; Nandi et al. 2022).

- **Used as the default verification truth** for rainfall and Tmax in backfill (`truth_source=AUTO`) and in stage 14 (**Use IMD grid**). Real-time files appear about 1–2 days after the valid day; ERA5 takes about 6.
- **Rainfall day convention.** IMD daily rainfall is the 24 h total ending 08:30 IST. VARUNA assigns it to the day the window starts, 08:30 IST D → 08:30 IST D+1. It aggregates the models' hourly forecasts over the same window (`IMD_RAIN_DAY_OFFSET_HOURS=9`). If your files follow the other convention, change the offset.
- **If the server cannot reach imdpune.gov.in,** download the `.grd` files in a browser and upload them: **Data sources → IMD gridded → Upload**, or `POST /api/india/imd-grid/upload`. The file size is validated against the grid layout.
- **No wind product.** IMD gridded data has none, so wind is verified against ERA5, and the report says so.

### NCMRWF forecast products (institutional access)

NCUM-G, NCUM-R and NEPS are not public; request access from NCMRWF (MoES). NCMRWF's data portal is [rds.ncmrwf.gov.in](https://rds.ncmrwf.gov.in). How delivered files get in:

1. Set `NCMRWF_DROP_DIR` to the folder where files arrive (SFTP drop, mounted share or bucket sync).
2. Run **Data sources → Scan drop folder**, or `POST /api/india/ncmrwf/scan`. A scheduled job can call the same endpoint.
3. Each new file is ingested as `AUTHORIZED_OPERATIONAL_FEED` and de-duplicated by SHA-256. Model ids such as `NCUM_G`, `NCMRWF_NCUM` and `NCUM_R` map to the `NCUM` slot.
4. Formats are those the ingestion engine reads: CSV, JSON, JSONL, Parquet, NetCDF and ZIP. Convert GRIB2 first, for example with `cdo` or `xarray` + `cfgrib`.

IMD's own GFS or WRF files enter the same way.

### IMD API (needs IMD approval)

IMD's [API reference](https://api.imd.gov.in/public/api_reference.html) lists these endpoints: `current_wx` (station observations, including last-24 h rainfall), `cityforecastloc`, `districtrainfall`, `districtwarning` (Day 1–5 warning colours) and `districtnowcast`.

- **Getting access.** It is granted per organisation; IMD's [API note](https://mausam.imd.gov.in/Forecast/marquee_data/API_doc.pdf) names a nodal officer to contact. Approval usually means whitelisting the server's IP.
- **After approval:** set `IMD_API_ENABLED=true`, plus `IMD_API_KEY` and `IMD_API_KEY_HEADER` if a key is issued.
- **Station map.** Set `IMD_STATION_MAP` for your regions. The built-in station ids, such as Hyderabad 43128, are a starting point and must be checked with IMD.
- **Endpoints:**
  - `GET /api/india/imd/observation?region_id=…` returns the latest station observation (wind converted from km/h to m/s).
  - `GET /api/india/imd/district-warning?district_id=…` returns IMD's own Day 1–5 colours, so you can compare them with VARUNA's extreme signal.

### Other Indian sources (manual upload today)

| Source | Use | Access |
|---|---|---|
| IMDAA reanalysis (12 km) | Long verification history | Free registration at rds.ncmrwf.gov.in; download NetCDF and upload |
| ISRO MOSDAC INSAT-3D/3DR rainfall | Rain over sparse-gauge areas and ocean | Free registration at [mosdac.gov.in](https://www.mosdac.gov.in/) |
| Bharat Forecast System (MoES 6 km) | Primary Indian NWP when shared | Through NCMRWF / IMD, same drop folder |

## Tier 2 — global public models over India

`POST /api/live/fetch` gets GFS, ECMWF IFS, ECMWF AIFS (AI), UK Met Office UM and DWD ICON from [Open-Meteo](https://open-meteo.com/en/docs) for the subdivision centroid. The previous-runs API supplies past forecasts for backfill. Every fetch is stored with its request URL, SHA-256 and the time it was received.

Limits:

- The UM is the same model family as NCUM but **is not NCUM**.
- The values are point extractions.
- Open-Meteo does not expose the exact model cycle on this endpoint.
- The free tier is for non-commercial use with attribution.

## Building verified skill

`POST /api/live/backfill {"region_id": "IN_TELANGANA_DECCAN", "variable": "rainfall", "days": 60, "truth_source": "AUTO"}`

1. Fetches what each model forecast 24 h and 48 h before each day.
2. Compares those forecasts with **IMD gridded** truth (ERA5 is the fallback, and the report's `truth_note` says when it was used).
3. Stores the per-day errors and writes MAE / RMSE / bias per model and lead (period `LIVE_BACKFILL_IMD`).
4. Fits the region's bias-corrected stacker, and reports a chronological hold-out: stacking vs average vs best single model.

The samples are small, so treat the results as indicative, not as published verification.

## Provenance labels shown in the UI

| Label | Meaning |
|---|---|
| `AUTHORIZED_OPERATIONAL_FEED` | NCMRWF / IMD file from the drop folder or an upload |
| `OBSERVATION_GRIDDED` | IMD gridded observation (verification truth) |
| `PUBLIC_API_FORECAST` | Global public model over India (reference lane) |
| `REANALYSIS_REFERENCE` | ERA5 (fallback truth, wind) |
| `SYNTHETIC_STRESS_TEST` / `SYNTHETIC_DEMO_SCENARIO` | Generated data — never presented as IMD/NCMRWF |

## Network checklist for the backend host

Outbound HTTPS is needed to:

- `imdpune.gov.in` (IMD gridded data)
- `api.imd.gov.in` (after approval)
- `*.open-meteo.com` (global models, ERA5)

Set `AIR_GAPPED_MODE=true` to block all of these. VARUNA then runs on uploaded and drop-folder files only.
