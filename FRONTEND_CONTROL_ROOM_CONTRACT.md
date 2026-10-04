# VARUNA — Frontend Control Room API Contract
**Problem Statement:** SIH26081 (MoES / NCMRWF — Adaptive Multi-Model Forecast Blending)  
**Document Purpose:** Complete, stabilized JSON response specification for the upcoming Control Room UI.  
**Frontend Rule:** The frontend never connects directly to database tables; it consumes exclusively this structured contract.

---

## 1. Meteorological Control Room Architecture Overview

The VARUNA Control Room UI is designed around the core operational loop:
$$\text{Data Ingest} \longrightarrow \text{Context} \longrightarrow \text{Trust Blending} \longrightarrow \text{Uncertainty} \longrightarrow \text{Explainability} \longrightarrow \text{Continuous Verification}$$

```
                ┌────────────────────────────────────────────────────────┐
                │        VARUNA Meteorological Operations Centre         │
                └──────────────────────────┬─────────────────────────────┘
                                           │
         ┌──────────────────┬──────────────┴───────┬────────────────────┐
         ▼                  ▼                      ▼                    ▼
   [Main Overview]   [Spatial Trust Map]    [Model Diagnostics]   [Verification Loop]
   /api/dashboard    /api/fusion/weight-map  /api/models          /api/verification
   /api/fusion       /api/fusion/trace      /api/what-changed    /api/experiments
```

---

## 2. API Endpoints & Stable JSON Contract

### 2.1 Main Dashboard Overview
**Endpoint:** `GET /api/dashboard/summary`  
**Parameters:**
- `region_id` (string, default: `IN_TELANGANA_HYDERABAD`)
- `variable` (string: `rainfall` | `temperature` | `wind_speed`)
- `lead_hours` (int: `24` | `48` | `72`)
- `weather_regime` (string: `NORMAL` | `HEAVY_RAINFALL` | `CONVECTIVE` | `TRANSITION_UNCERTAIN`)

**Response:**
```json
{
  "active_cycle": "2026-09-26T00:00:00Z",
  "region_id": "IN_TELANGANA_HYDERABAD",
  "variable": "rainfall",
  "lead_hours": 48,
  "weather_regime": "HEAVY_RAINFALL",
  "season": "SW_MONSOON",
  "fused_forecast": 74.2,
  "unit": "mm",
  "baselines": {
    "simple_average": 74.0,
    "static_blend": 71.9
  },
  "model_forecasts": {
    "NCUM": 82.0,
    "GFS": 103.0,
    "WRF": 47.0,
    "AI_WEATHER": 64.0
  },
  "weights": [
    {
      "model_id": "NCUM",
      "weight": 0.4431,
      "raw_forecast": 82.0,
      "historical_mae": 9.2,
      "recent_bias": 0.0,
      "confidence_contribution": 0.384,
      "status": "ACTIVE",
      "notes": ["Dominant weight assigned due to high monsoon trough skill."]
    },
    {
      "model_id": "WRF",
      "weight": 0.2852,
      "raw_forecast": 47.0,
      "historical_mae": 11.4,
      "status": "ACTIVE"
    },
    {
      "model_id": "AI_WEATHER",
      "weight": 0.1714,
      "raw_forecast": 64.0,
      "historical_mae": 11.8,
      "status": "ACTIVE"
    },
    {
      "model_id": "GFS",
      "weight": 0.1003,
      "raw_forecast": 103.0,
      "historical_mae": 18.5,
      "status": "ACTIVE",
      "notes": ["Penalized due to historical wet bias under heavy monsoon regime."]
    }
  ],
  "disagreement": {
    "disagreement_level": "HIGH",
    "disagreement_score": 0.812,
    "forecast_spread": 23.8,
    "weighted_spread": 21.2,
    "range": 56.0,
    "variance": 566.4
  },
  "uncertainty": {
    "probability": 72.4,
    "probability_indicator": 72.4,
    "is_calibrated_probability": false,
    "confidence": "MEDIUM",
    "confidence_score": 0.553,
    "uncertainty_margin": 32.5,
    "threshold": 64.5
  },
  "provenance": "SYNTHETIC_STRESS_TEST"
}
```

---

### 2.2 Dynamic Spatial Model-Weight Map (GeoJSON)
**Endpoint:** `GET /api/fusion/weight-map`  
**Parameters:** `variable`, `lead_hours`, `season`, `weather_regime`, `strategy`  
**Format:** RFC 7946 GeoJSON `FeatureCollection` ready for Leaflet / Mapbox / Deck.gl.

**Feature Properties Contract:**
```json
{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [[[77.5, 17.0], [79.5, 17.0], [79.5, 19.5], [77.5, 19.5], [77.5, 17.0]]] },
  "properties": {
    "id": "IN_TELANGANA",
    "subdivision_name": "Telangana",
    "state": "Telangana",
    "lead_hours": 48,
    "dominant_model": "NCUM",
    "dominant_weight": 0.4431,
    "weights": {
      "NCUM": 0.4431,
      "WRF": 0.2852,
      "AI_WEATHER": 0.1714,
      "GFS": 0.1003
    },
    "sum_of_weights": 1.0,
    "blending_strategy": "ADAPTIVE_ML_META_MODEL",
    "meteorological_rationale": "NCUM global model prioritized for monsoon low-pressure trough tracking; GFS penalized due to known wet bias."
  }
}
```

---

### 2.3 Scientific Provenance Trace (`ForecastTrace`)
**Endpoint:** `GET /api/fusion/trace`  
**Purpose:** Answers "Why did VARUNA trust model X over Y, what data was ingested, what uncertainty exists, and what is the audit trail?"

**Response Structure:**
```json
{
  "trace_id": "TRACE_9B4F81A721C0",
  "forecast_cycle_id": "CYCLE_IN_TELANGANA_HYDERABAD_48H",
  "generated_at": "2026-09-28T05:00:00Z",
  "region_id": "IN_TELANGANA_HYDERABAD",
  "variable": "rainfall",
  "lead_hours": 48,
  "data_provenance_badge": "SYNTHETIC_STRESS_TEST",
  "sources": [
    {
      "model_id": "NCUM",
      "raw_value": 82.0,
      "canonical_value": 82.0,
      "unit": "mm",
      "resolution": "12km",
      "source_agency": "NCMRWF / MoES",
      "provenance_badge": "SYNTHETIC_STRESS_TEST",
      "authorization_status": "AUTHORIZED_PROVIDER_REQUIRED",
      "is_available": true
    },
    {
      "model_id": "GFS",
      "raw_value": 103.0,
      "canonical_value": 103.0,
      "unit": "mm",
      "resolution": "25km",
      "source_agency": "NOAA / NCEP",
      "provenance_badge": "PUBLIC_BENCHMARK",
      "authorization_status": "ACTIVE_PUBLIC",
      "is_available": true
    }
  ],
  "harmonization": {
    "unit_conversions_applied": ["native_to_canonical"],
    "spatial_resampling_method": "SUBDIVISION_AVERAGE",
    "target_resolution": "subdivision_centroid",
    "physical_bounds_status": "PASSED"
  },
  "context": {
    "region_id": "IN_TELANGANA_HYDERABAD",
    "season": "SW_MONSOON",
    "lead_hours": 48,
    "weather_regime": "HEAVY_RAINFALL",
    "variable": "rainfall"
  },
  "trust_weights": [
    { "model_id": "NCUM", "weight": 0.4431 },
    { "model_id": "WRF", "weight": 0.2852 },
    { "model_id": "AI_WEATHER", "weight": 0.1714 },
    { "model_id": "GFS", "weight": 0.1003 }
  ],
  "blending_strategy": "ADAPTIVE_ML",
  "weights_sum": 1.0,
  "disagreement": {
    "disagreement_level": "HIGH",
    "disagreement_score": 0.812,
    "forecast_spread": 23.8,
    "weighted_spread": 21.2
  },
  "fusion": {
    "fused_value": 74.2,
    "simple_average": 74.0,
    "static_blend": 71.9,
    "status": "OPTIMAL_MULTI_MODEL_FUSION"
  },
  "uncertainty": {
    "confidence": "MEDIUM",
    "confidence_score": 0.553,
    "uncertainty_margin": 32.5,
    "is_calibrated_probability": false
  },
  "ml_model_metadata": {
    "version": "v1.0.0-bootstrap",
    "provenance": "SYNTHETIC_TEMPORAL_BENCHMARK",
    "feature_count": 22
  },
  "verification_history": {
    "recent_verified_mae": 9.2,
    "evaluation_window": "2024-2026_monsoon_temporal_split",
    "sample_count": 150
  }
}
```

---

### 2.4 Dataset Registry & Ingestion Status
**Endpoints:**
- `GET /api/datasets`: List registered datasets, coverage, checksums, and records
- `POST /api/datasets/ingest`: Chunked memory-safe ingestion endpoint
- `GET /api/datasets/{dataset_id}/records?limit=50&offset=0`: Paginated canonical records

**Dataset Entry Contract:**
```json
{
  "dataset_id": "IMDAA_REANALYSIS_12KM",
  "name": "Indian Monsoon Data Assimilation and Analysis (IMDAA) 12km Reanalysis",
  "source": "NCMRWF / IMD / UK Met Office",
  "version": "v1.0-4DVAR",
  "format": "NETCDF / CSV",
  "variables": ["rainfall", "temperature", "wind_speed"],
  "spatial_coverage": "INDIAN_MONSOON_REGION (0-45N, 30-120E)",
  "resolution": "12 km",
  "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "record_count": 500,
  "status": "AVAILABLE",
  "provenance_badge": "PUBLIC_BENCHMARK"
}
```

---

### 2.5 Reproducible Benchmark Experiments
**Endpoints:**
- `POST /api/experiments/run`: Launches reproducible chronological split evaluation
- `GET /api/experiments`: Lists historical experiments
- `GET /api/experiments/{id}`: Detailed result matrices and partitions
- `GET /api/experiments/{id}/report`: Plain-text Markdown report

**Experiment Result Table Contract:**
```json
{
  "experiment_id": "EXP_TEMPORAL_20260928_051200",
  "provenance_qualification": "SYNTHETIC / DEMONSTRATION BENCHMARK",
  "chronological_partitions": {
    "train": { "start": "2024-06-01", "end": "2025-03-27", "samples": 300 },
    "validation": { "start": "2025-03-28", "end": "2025-06-10", "samples": 75 },
    "test": { "start": "2025-06-11", "end": "2025-10-13", "samples": 125 },
    "total_samples": 500
  },
  "results_table": [
    {
      "method": "NCUM",
      "mae": 9.21,
      "rmse": 11.45,
      "bias": 0.48,
      "correlation": 0.985,
      "sample_count": 125,
      "csi": 0.65
    },
    {
      "method": "SIMPLE_AVERAGE",
      "mae": 13.82,
      "rmse": 16.10,
      "bias": 3.12,
      "correlation": 0.978,
      "sample_count": 125,
      "csi": 0.68
    },
    {
      "method": "ADAPTIVE_ML_META_MODEL",
      "mae": 8.52,
      "rmse": 10.35,
      "bias": -0.15,
      "correlation": 0.995,
      "sample_count": 125,
      "csi": 0.81,
      "brier": 0.042
    }
  ],
  "scientific_findings": {
    "ml_mae_reduction_vs_simple_average_pct": 38.35,
    "conclusion": "On 125 unseen test days, Adaptive ML Meta-Model achieved an MAE of 8.52 mm (sample count: 125), representing a +38.4% error reduction over Simple Average (13.82 mm). DATA PROVENANCE: SYNTHETIC / DEMONSTRATION BENCHMARK."
  }
}
```

---

### 2.6 Background Job Execution
**Endpoints:**
- `POST /api/jobs/benchmark`: Asynchronous benchmark dispatch
- `POST /api/jobs/ingest`: Asynchronous dataset ingest
- `POST /api/jobs/recalibrate`: Asynchronous model retraining & skill update
- `GET /api/jobs/{job_id}`: Poll job status (`QUEUED` | `RUNNING` | `COMPLETED` | `FAILED`)

**Job Status Contract:**
```json
{
  "job_id": "JOB_BENCHMARK_20260928_051500_A1B2C3",
  "job_type": "benchmark",
  "status": "COMPLETED",
  "progress_pct": 100.0,
  "created_at": "2026-09-28T05:15:00Z",
  "completed_at": "2026-09-28T05:15:03Z",
  "duration_seconds": 3.12,
  "result": { ... },
  "error_message": null
}
```

---

## 3. UI Screen to API Mapping Guide

| Control Room Screen | Primary APIs Consumed | Key Interactive Features |
| :--- | :--- | :--- |
| **Operational Overview** | `GET /api/dashboard/summary`<br>`GET /api/what-changed` | Live forecast, baselines comparison, severe weather warning flags, "What Changed Since Yesterday's Cycle" |
| **Dynamic Spatial Weight Map** | `GET /api/fusion/weight-map`<br>`GET /api/regions/subdivisions` | Interactive Leaflet/Mapbox choropleth, lead-time slider (24h $\to$ 48h $\to$ 72h), dominant model coloring |
| **Model Trust & Reliability Diagnostics** | `GET /api/fusion/weights`<br>`GET /api/models/{id}/skill`<br>`POST /api/demo/failure-injection` | Trust weight dials, historical MAE by regime, live failure injection controls (GFS bias, missing model) |
| **Explainable AI (XAI) Inspector** | `GET /api/fusion/explanation`<br>`GET /api/fusion/trace` | Structured 'Why this forecast?', dominant model allocation factors, full scientific audit trace |
| **Scientific Verification Benchmark** | `GET /api/experiments`<br>`POST /api/experiments/run`<br>`GET /api/experiments/{id}/report` | Continuous verification metrics, empirical comparison table, exportable Markdown verification reports |
| **Dataset Ingestion & Pipeline Monitor** | `GET /api/datasets`<br>`POST /api/datasets/ingest`<br>`GET /api/jobs/{id}` | Dataset catalog, upload modal, background job status, record pagination |
