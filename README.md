# VARUNA: Adaptive Forecast Intelligence Platform
## SIH26081: Hybrid AI–NWP Multi-Model Forecast Blending System

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-11%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-Government--Ready-orange.svg)]()

> **Ministry of Earth Sciences (MoES) | National Centre for Medium Range Weather Forecasting (NCMRWF)**  
> **Problem Statement ID:** SIH26081 | **Theme:** Disaster Management | **Category:** Software

---

## 1. Executive Summary & Core Positioning

### The Fundamental Insight
India already possesses sophisticated meteorological and numerical weather prediction infrastructure. The **National Centre for Medium Range Weather Forecasting (NCMRWF)** operates state-of-the-art numerical modeling systems, including the **NCUM (NCMRWF Unified Model)** and **NEPS (NCMRWF Ensemble Prediction System)**, alongside regional models like WRF and emerging data-driven AI weather models.

**The operational challenge is not a shortage of raw forecasts.**  
Different forecasting systems excel under different conditions:
- **NCUM** exhibits exceptional synoptic accuracy over the monsoon trough.
- **WRF** offers 3 km convective-resolving mesoscale detail at short lead times (24h/48h).
- **GFS** provides long-horizon synoptic tracking, but can develop wet bias in peninsular topography.
- **AI Weather Models** achieve rapid global pattern consistency, but may smooth localized convective spikes.

### Our Core Identity: The Intelligence Layer
```
"Don't ask which weather model is the best.
Ask which model should be trusted, where, when, and by how much."
```
VARUNA acts as a **context-aware, adaptive forecast intelligence and fusion platform** sitting directly between heterogeneous model outputs and operational meteorologists. It dynamically determines trust weights, quantifies epistemic uncertainty, preserves failure memory, and generates explainable decisions.

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                      LAYER 1: FORECAST SOURCES                         │
│       NCUM (12km) │ GFS (25km) │ WRF (3km) │ AI Weather (0.25°)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│                   LAYER 2: DATA HARMONIZATION & QC                     │
│     Unit Conversion │ Physical Range Validation │ Missing Handling     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│                  LAYER 3: HISTORICAL SKILL ENGINE                      │
│     MAE │ RMSE │ Bias │ Correlation │ Regime Skill │ Recent Bias       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│                      LAYER 4: CONTEXT ENGINE                           │
│     Region │ Season │ Lead Time (24h/48h/72h) │ Synoptic Regime        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│                     LAYER 5: ADAPTIVE TRUST AI                         │
│     Simplex Dynamic Weights (w_i >= 0, Σw_i = 1) │ Failure Memory     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│                     LAYER 6: FORECAST FUSION                           │
│     Fused Estimate = Σ(w_i × F_i) │ Simple Average │ Static Blend      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│              LAYER 7: UNCERTAINTY & DECISION GUIDANCE                  │
│     Event Probability vs Evidence Confidence │ Model Disagreement      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│                  LAYER 8: EXPLAINABILITY & AUDIT                       │
│     "Why This Forecast?" │ "What Changed?" │ Failure Injection Controls│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    └────────────────────┐
                                                         ↓
                                                CONTINUOUS VERIFICATION
                                                Actual vs Forecast -> Update
```

---

## 3. Five Core Innovations

1. **Adaptive Trust Allocation:** Dynamic weighting conditioned on region, season, lead time (24h/48h/72h), and weather regime (`NORMAL`, `HEAVY_RAINFALL`, `CONVECTIVE`, `TRANSITION_UNCERTAIN`).
2. **Disagreement-Aware Confidence:** Multi-model spread ($S$) is explicitly treated as an uncertainty signal. **Event probability is strictly separated from evidence confidence** (e.g., Heavy Rainfall Probability = 78%, but Confidence = MODERATE due to model divergence).
3. **Model Failure Memory:** Historical vulnerabilities and short-term operational bias spikes down-weight compromised models automatically.
4. **Transparent Explainability (XAI):** Structured diagnostics answering *"Why this forecast?"* (dominant factors, bias adjustments) and *"What changed?"* (cycle-to-cycle shifts and primary meteorological drivers).
5. **Continuous Verification Loop:** Temporal verification benchmarks against three baselines (Individual Models, Simple Average, Static Blend) to prove the value added by adaptive blending.

---

## 4. Mathematical Formulation

### 1. Model Reliability Score
For each active model $i \in \{1, \dots, N\}$:
$$R_i = \left(\frac{1}{\max(\text{MAE}_{i, \text{hist}}, 1.0)}\right) \times \left(\frac{1}{1.0 + \frac{\text{RecentError}_i}{15.0}}\right) \times V_i(\text{regime}, \text{lead})$$
where $V_i$ represents the regime-specific vulnerability multiplier from Failure Memory.

### 2. Simplex Normalized Weights
$$\tilde{w}_i = \begin{cases} R_i & \text{if model is ACTIVE} \\ 0 & \text{if model is DISABLED / MISSING} \end{cases}$$
$$w_i = \frac{\tilde{w}_i}{\sum_{j=1}^N \tilde{w}_j} \quad \text{such that } w_i \ge 0 \text{ and } \sum_{i=1}^N w_i = 1.0$$

### 3. Fused Estimate
$$F_{\text{fused}} = \sum_{i=1}^N w_i \cdot F_i$$

### 4. Epistemic Confidence Rating
$$C_{\text{score}} = 1.0 - (0.55 \times \text{DisagreementScore}) - (0.25 \times \text{MissingRatio}) - (0.20 \times \text{LeadDecay})$$

---

## 5. Frozen MVP Scope

| Parameter | MVP Scope Specification |
| :--- | :--- |
| **Forecast Sources** | **NCUM** (National NWP), **GFS** (Global NWP), **WRF** (Regional Mesoscale), **AI Weather Model** (ML) |
| **Variables** | **Rainfall (mm)** [Primary hero demo], **Temperature (°C)**, **Wind Speed (km/h)** |
| **Lead Times** | **24h**, **48h**, **72h** |
| **Geographic Scope** | India $\rightarrow$ Telangana (Hyderabad, Adilabad, Warangal) + Kerala (Wayanad) |
| **Weather Regimes** | `NORMAL`, `HEAVY_RAINFALL`, `CONVECTIVE`, `TRANSITION_UNCERTAIN` |
| **Hero Demonstration** | 48-hour rainfall forecast during an active southwest monsoon depressional event |
| **Data Provenance** | Explicit separation: `synthetic_demo` \| `historical_public` \| `authorized_operational` |

---

## 6. API Reference

FastAPI Swagger documentation is live locally and in production at:  
👉 **`/api/docs`**

### Summary of Available Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service and database operational status |
| `GET` | `/api/models` | List registered forecasting systems (NCUM, GFS, WRF, AI) |
| `GET` | `/api/models/{model_id}/skill` | Conditional historical performance by regime and lead time |
| `GET` | `/api/forecasts` | Raw harmonized forecasts with quality control flags |
| `GET` | `/api/fusion/current` | Active fused forecast with weights, disagreement, and confidence |
| `GET` | `/api/fusion/weights` | Normalized trust weights verifying $\sum w_i = 1.0$ |
| `GET` | `/api/fusion/explanation` | Explainable decision support: "Why this forecast?" |
| `GET` | `/api/what-changed` | Consecutive cycle diagnostics and primary shift drivers |
| `GET` | `/api/regions/{id}/forecast` | Spatially localized grid forecast with GIS centroid |
| `GET` | `/api/extremes` | Non-operational decision guidance for heavy rain, heatwave, gale |
| `GET` | `/api/verification/compare` | Scientific benchmark: Individual vs Simple Avg vs Static vs Adaptive |
| `GET` | `/api/dashboard/summary` | Complete unified state for frontend operations dashboard |
| `GET` | `/api/demo/scenarios` | List 7 pre-configured signature demonstration scenarios |
| `POST`| `/api/demo/load-scenario/{id}`| Load scenario (e.g. Signature Heavy Monsoon, High Disagreement) |
| `POST`| `/api/demo/inject-failure` | Inject runtime faults: model bias, missing feed, or disagreement |

---

## 7. Interactive Judge Demonstration Sequence

```
Step 1: Inspect 4 Disagreeing Forecasts (NCUM: 82mm, WRF: 47mm, GFS: 103mm, AI: 64mm)
        --> API detects: Disagreement HIGH (std dev: 23.5 mm)

Step 2: Context Retrieved (Telangana | 48h lead | SW Monsoon | Heavy Rainfall Regime)

Step 3: Historical Skill & Failure Memory Evaluated
        --> NCUM prioritized due to monsoon trough 4D-Var data assimilation
        --> GFS penalized for peninsular wet bias

Step 4: AI Engine Computes Dynamic Trust Weights
        --> NCUM: 38.5%, WRF: 34.2%, GFS: 14.1%, AI: 13.2% (Sum = 100%)

Step 5: Fused Forecast Produced: 71.4 mm
        --> Heavy Rain Probability: 76.5%
        --> Confidence: MODERATE (explicitly uncoupled from probability)

Step 6: "Why This Forecast?" Explains Evidence to Meteorologist

Step 7: Runtime Fault Injection: POST /api/demo/inject-failure (simulate_missing_model: NCUM)
        --> NCUM weight drops to 0.0%
        --> Remaining sources re-normalize automatically
        --> Confidence rating decreases; data health flags DEGRADED_AVAILABILITY

Step 8: Verification Benchmark Proves Adaptive Value
        --> MAE reduction compared to simple multi-model average
```

---

## 8. Local Setup & Testing

### Prerequisites
- Python 3.11+
- Virtual environment tool (`venv` or `virtualenv`)

### Installation
```bash
# Clone the repository
git clone https://github.com/your-username/varuna-sih26081.git
cd varuna-sih26081

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests
Execute the complete automated test suite verifying all 11 scientific and mathematical invariants:
```bash
pytest backend/tests/test_all.py -v
```

### Starting the Server
```bash
# Start FastAPI with hot reload
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser to:
- **Swagger UI:** [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
- **Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Dashboard API:** [http://127.0.0.1:8000/api/dashboard/summary](http://127.0.0.1:8000/api/dashboard/summary)

---

## 9. Render Deployment Instructions

This repository is pre-configured for one-click deployment on **Render**:
1. Connect your GitHub repository to [Render.com](https://render.com).
2. Create a new **Web Service** using the repo root:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables:**
     - `PYTHONPATH` = `backend`
     - `ENVIRONMENT` = `production`
     - `SECRET_KEY` = `(Generate secure key)`
     - `DATABASE_URL` = `(Attach Render PostgreSQL or leave unset to use SQLite default)`
3. Alternatively, deploy via `render.yaml` Blueprint directly from Render dashboard.

---

## 10. Scientific Claims vs Limitations

| We Legitimized & Verified | We Strictly Do NOT Claim |
| :--- | :--- |
| Dynamic multi-model weight calculation | Direct live feed into operational NCMRWF mainframes without MoES approval |
| Disagreement-aware uncertainty quantification | Replacing operational meteorologists or autonomous disaster dispatch |
| Graceful missing-source re-normalization | 100% forecasting accuracy or zero atmospheric uncertainty |
| Explainable evidence factors | Superiority over operational agencies without formal institutional evaluation |
| Reproducible synthetic stress scenarios | Fabricated accuracy statistics |

---
**VARUNA** | Smart India Hackathon 2026 | Ministry of Earth Sciences (MoES) / NCMRWF
