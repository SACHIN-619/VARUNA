# VARUNA Scientific Benchmark & Provenance Audit Report
**Problem Statement ID:** SIH26081 (MoES / NCMRWF — Disaster Management)  
**System Name:** VARUNA (Adaptive Forecast Intelligence Platform)  
**Audit Date:** 2026-09-26  
**Auditor Classification:** Lead Research & System Architecture Audit  
**Audit Status:** `COMPLETE — PROVENANCE FORMALLY CLASSIFIED`

---

## Executive Summary & Core Audit Verdict

Following a rigorous source-code and data-artifact audit of the VARUNA forecasting system, this report provides a transparent, scientifically unvarnished assessment of the benchmark results previously reported (`3.16 mm MAE` / `+38.3% error reduction`).

### Verdict in Brief:
1. **Provenance Classification:** The 500-day evaluation dataset is **100% SYNTHETIC DATA (`VERIFIED_SYNTHETIC`)**. No raw public NetCDF/GRIB files from NCMRWF, IMD, or NOAA were ingested onto disk.
2. **Leakage Audit & Root-Cause Discovery:** The previously reported `3.16 mm MAE` (+38.3% gain) was the result of a **same-day error leakage** in the synthetic generator (`recent_errors` on day $t$ incorporated the instantaneous error of day $t$).
3. **Causal Benchmark Reproduction:** With same-day leakage strictly eliminated and replaced with a causal Exponential Moving Average (EMA) of verified historical errors ($t < \text{current}$), the strictly causal out-of-sample result on 150 held-out test days is:
   * **Simple Multi-Model Average:** `5.12 mm MAE` (RMSE: `6.59 mm`)
   * **Adaptive ML Meta-Model:** **`4.90 mm MAE`** (RMSE: `6.49 mm`)
   * **Genuine Causal Skill Gain:** **`+4.3% error reduction`** (not +38.3%).
4. **Spatial Weight Maps:** The 14-subdivision weight maps are dynamically calculated using physical heuristics and GBDT inference, but the underlying terrain performance bonuses and textual briefing explanations are currently **physics-informed parameterizations / template hypotheses**, not empirical deductions from station archives.
5. **Presentation Guidance:** The `3.16 mm / +38.3%` claim **MUST NOT be presented as real-world forecast skill** in SIH deliverables. The project should be presented as an **end-to-end engineered software architecture with a verified synthetic stress-test benchmark**, ready for institutional onboarding of actual MoES reanalysis datasets.

---

## A. Dataset Provenance Audit

| Attribute | Audited Reality |
| :--- | :--- |
| **Total Benchmark Cycles** | 500 simulated days |
| **Physical Files on Disk** | 0 CSV, 0 NetCDF, 0 GRIB, 0 Parquet |
| **Generation Mechanism** | In-memory stochastic simulation via NumPy (`benchmark_runner.py`) |
| **Random Seed** | Hardcoded fixed seed: `101` |
| **True Data Provenance** | `SYNTHETIC_DATA` / `VERIFIED_SYNTHETIC` |
| **Geographic Grounding** | Simulated reference point: `IN_TELANGANA_HYDERABAD` ($17.385^\circ\text{N}, 78.4867^\circ\text{E}$) |
| **Variable Analyzed** | 24-hour accumulated rainfall (mm) |

```json
{
  "total_days": 500,
  "training_days": 350,
  "unseen_test_days": 150,
  "real_public_records": 0,
  "synthetic_records": 2500,
  "provenance": "VERIFIED_SYNTHETIC"
}
```

---

## B. Forecast Sources Provenance Audit

The benchmark evaluates four forecast streams. Their actual technical provenance in the codebase is as follows:

1. **NCUM (12 km National NWP):**
   * **Source in code:** `benchmark_runner.py` (lines 62, 70).
   * **Formula:** $\text{Forecast} = \text{Observation} + \mathcal{N}(0.5, 9.0 + \text{lead\_factor})$.
   * **Classification:** `SYNTHETIC_DATA`.
   * **Operational Adapter:** `NCUMProvider` in `providers.py` returns static representative demo values (e.g. 82.0 mm).
2. **GFS (25 km Global NWP):**
   * **Source in code:** `benchmark_runner.py` (lines 64, 71).
   * **Formula:** $\text{Forecast} = \text{Observation} + \mathcal{N}(12.5, 14.0 + 1.5 \times \text{lead\_factor})$ under heavy rain regime.
   * **Classification:** `SYNTHETIC_DATA` (reflecting known wet-bias behavior).
   * **Operational Adapter:** `GFSProvider` in `providers.py` returns static demo values (103.0 mm).
3. **WRF (3 km Regional Mesoscale):**
   * **Source in code:** `benchmark_runner.py` (lines 66, 72).
   * **Formula:** $\text{Forecast} = \text{Observation} + \mathcal{N}(-1.5, 7.5)$ for short lead convective, dispersing at 72h.
   * **Classification:** `SYNTHETIC_DATA`.
   * **Operational Adapter:** `WRFProvider` returns static demo values (47.0 mm).
4. **AI Weather Model (0.25° Data-Driven Transformer/GNN):**
   * **Source in code:** `benchmark_runner.py` (lines 68, 73).
   * **Formula:** $\text{Forecast} = \text{Observation} + \mathcal{N}(-3.5, 10.5)$ with peak smoothing.
   * **Classification:** `SYNTHETIC_DATA`.

---

## C. Observation / Reference Truth Provenance

The system references two ground-truth abstractions:
1. **`IMDAAObservationProvider` (`observation_provider.py`):**
   * **Claimed Role:** Indian Monsoon Data Assimilation and Analysis 12km reanalysis.
   * **Actual Code Implementation:** Lines 80–98 generate synthetic random exponential values:
     `obs_val = round(max(0.0, float(np.random.exponential(scale=25.0))), 1)`.
   * **Classification:** `FUTURE_PROVIDER_ONLY` / `SIMULATED_REANALYSIS_INTERFACE`. No actual IMDAA NetCDF files exist in the repository.
2. **`StationObservationProvider` (`observation_provider.py`):**
   * **Claimed Role:** IMD Automatic Weather Station (AWS) network.
   * **Actual Code Implementation:** Returns fixed mock observation (`71.2 mm`).
   * **Classification:** `DEMO_DATA`.
3. **Reanalysis vs. In-Situ Distinction:**
   * Crucially, IMDAA is a **numerical atmospheric reanalysis** (combining NWP model physics with data assimilation), **NOT direct ground truth**.
   * VARUNA's architecture now formally categorizes them as:
     * `STATION_OBSERVATION`: Direct in-situ physical measurements (rain gauges, AWS).
     * `REANALYSIS_REFERENCE`: Model-assimilated gridded states (IMDAA, ERA5).
     * `SYNTHETIC_STRESS_TEST`: Artificially synthesized test series.

---

## D. Temporal Split Audit

* **Temporal Horizon:** 500 chronological daily cycles starting `2024-06-01T00:00:00Z`.
* **Split Boundary:**
  * **Training Period:** Days 1 to 350 (`2024-06-01` to `2025-05-16`) $\rightarrow$ 350 samples (70%).
  * **Held-Out Test Period:** Days 351 to 500 (`2025-05-17` to `2025-10-13`) $\rightarrow$ 150 samples (30%).
* **Chronological Invariant:** $\text{TRAIN} < \text{TEST}$ chronologically. Test samples were never present in the GBDT training matrix `X_train`.

---

## E. Feature Construction (22-Dimensional Feature Vector)

For each forecast cycle, `ml_trust_model.py` constructs a fixed 22-dimensional feature vector $\mathbf{x} \in \mathbb{R}^{22}$:
1. **Raw Forecasts (4 features):** $F_{\text{NCUM}}, F_{\text{GFS}}, F_{\text{WRF}}, F_{\text{AI}}$.
2. **Ensemble Spread Metrics (3 features):** Mean forecast ($\mu_F$), Standard deviation ($\sigma_F$), Range ($\max F - \min F$).
3. **Historical Climatological Skill (4 features):** Published baseline MAE for each model ($8.0 \dots 18.5$ mm).
4. **Historical Climatological Bias (4 features):** Historical systematic bias for each model.
5. **Recent Operational Verification Errors (4 features):** Causal Exponential Moving Average ($\text{EMA}_{t-1}$) of recent verified forecast errors.
6. **Contextual Regime (3 features):** Lead time (hours: 24, 48, 72), Weather Regime index (0–3), Season index (0–4).

---

## F. ML Meta-Model Architecture

* **Model Class:** `sklearn.ensemble.GradientBoostingRegressor`.
* **Sub-Models:** 4 independent regressors (one per model $m \in \{\text{NCUM}, \text{GFS}, \text{WRF}, \text{AI}\}$).
* **Target Variable:** Absolute forecast error residual $Y_m = |F_m - O|$.
* **Hyperparameters:**
  * `n_estimators = 60`
  * `max_depth = 3`
  * `learning_rate = 0.08`
  * `loss = 'squared_error'`
  * `random_state = 42`
* **Simplex Output Transformation:**
  Predicted errors $\hat{e}_m = \hat{f}_m(\mathbf{x})$ are converted to convex simplex trust weights via temperature-scaled softmax:
  $$w_m = \frac{\exp(-\hat{e}_m / \tau)}{\sum_{k \in \mathcal{M}_{\text{active}}} \exp(-\hat{e}_k / \tau)}$$
  where $\tau = 12.0$, ensuring $w_m \ge 0$ and $\sum w_m \equiv 1.0$.

---

## G. Leakage Audit & Reconciliation of the 3.16 mm vs 4.90 mm Result

During our audit, we identified the exact mathematical mechanism that generated the previously reported `3.16 mm` MAE:

```python
# PREVIOUS (LEAKY) CODE in benchmark_runner.py (Line 83):
recent = {
    "NCUM": round(abs(err_ncum) * 0.4, 1),
    "GFS":  round(abs(err_gfs)  * 0.5, 1),
    ...
}
```

### The Flaw:
`err_ncum` was the error of the **current day's forecast** ($F_{t} - O_{t}$). By injecting $0.4 \times |e_t|$ into the feature vector $\mathbf{x}_t$, the GBDT regressor received an **instantaneous proxy for the true error of day $t$** before making its prediction. This constitutes instantaneous target leakage.

### The Fix (Strict Causality):
`recent_errors` at forecast time $t$ was refactored to depend strictly on verified errors from previous cycles ($t-1, t-2, \dots$) using an Exponential Moving Average ($\alpha = 0.20$):
$$\text{EMA}_t(m) = 0.20 \cdot |F_{t-1}(m) - O_{t-1}| + 0.80 \cdot \text{EMA}_{t-1}(m)$$

### Reconciled Metrics:
* **Leaky Simulation (Invalid):** ML MAE = `3.16 mm` (+38.3% gain over simple average).
* **Strictly Causal Simulation (Audited & True):** ML MAE = `4.90 mm` (**+4.3% gain over simple average**).

---

## H. Benchmark Baselines & Test Results

Evaluated across the **150 held-out unseen test days** under strictly causal conditions:

| Method | Paradigm | MAE (mm) | RMSE (mm) | Bias (mm) | Correlation ($r$) | CSI ($\ge 64.5$ mm) | Brier Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **GFS** | Individual Global NWP | 11.72 | 15.12 | +5.07 | 0.949 | 0.676 | — |
| **WRF** | Individual Regional Mesoscale | 11.24 | 14.83 | +0.70 | 0.932 | 0.815 | — |
| **AI Weather Model** | Individual ML Forecast | 8.74 | 11.69 | +0.73 | 0.959 | 0.714 | — |
| **NCUM** | Individual National NWP | 7.64 | 10.19 | +0.46 | 0.970 | 0.893 | — |
| **Simple Multi-Model Average** | Baseline 1 (Equal 25% Weights) | 5.12 | 6.59 | +1.74 | 0.988 | 1.000 | — |
| **Static Operational Blend** | Baseline 2 (Fixed Weights) | 5.45 | 6.94 | +1.48 | 0.986 | 1.000 | — |
| **Adaptive Reliability Baseline**| Baseline 3 (Heuristic Rules) | 5.04 | 6.57 | +1.18 | 0.987 | 1.000 | — |
| **Adaptive ML Meta-Model** | **VARUNA Learned ML (Audited)**| **4.90** | **6.49** | **+0.27** | **0.987** | **1.000** | **0.040** |

### Verified Skill Advantage (Causal Synthetic):
* **Error Reduction vs. Best Individual Model (NCUM 7.64 mm):** **`-35.9% MAE`**.
* **Error Reduction vs. Simple Average (5.12 mm):** **`-4.3% MAE`** (Bias reduced from `+1.74 mm` to `+0.27 mm`).
* **Error Reduction vs. Static Blend (5.45 mm):** **`-10.1% MAE`**.

---

## I. Audit of 14-Subdivision Spatial Weight Maps

| Subdivision Claim | Audited Reality | Classification |
| :--- | :--- | :---: |
| **"WRF dominant at 24h in Western Ghats"** | Hardcoded bonus `wrf_orographic_bonus_24h = 0.25` in `spatial_weight_map.py` | `PHYSICAL_HYPOTHESIS` |
| **"NCUM dominant along Monsoon Trough"** | Parameterized lower base MAE for NCUM in central river basins | `PHYSICAL_HYPOTHESIS` |
| **"GFS penalized for peninsular wet bias"** | Parameterized penalty `gfs_bias_penalty = 0.35` | `PHYSICAL_HYPOTHESIS` |
| **"AI Weather Model dominant at 72h"** | Parameterized lead-time error slope `(lead_hours - 24) * 0.04` | `PHYSICAL_HYPOTHESIS` |
| **Weight Computation ($w_i$)** | Executed dynamically via `ml_trust_model.predict_weights()` | `DYNAMIC_CALCULATION` |
| **Briefing Text ("Why this model?")** | Programmatic template strings formatted from dictionary keys | `TEMPLATE_EXPLANATION` |

**Conclusion:** The spatial weight maps are **dynamically computed**, but they are driven by **domain-informed physical parameter tables**, not empirical training on historical IMDAA reanalysis grids.

---

## J. Reproducibility Protocol

To reproduce the audited causal benchmark results:

```bash
# 1. Activate environment
cd backend
$env:PYTHONPATH="."

# 2. Run benchmark directly
python -c "from app.experiments.benchmark_runner import benchmark_runner; res = benchmark_runner.run_experiment(); print(res['scientific_findings'])"

# Expected output:
# Simple Average MAE: 5.12 mm
# Adaptive ML MAE:    4.90 mm
# Causal Skill Gain:  +4.30%
```

---

## K. Known Scientific Limitations

1. **No External Gridded Ingestion Yet:** Raw NetCDF/GRIB files from ECMWF Open Data, NOAA GFS archives, or IMD gridded products have not yet been downloaded to the local filesystem.
2. **Point Simulation vs Spatial Grid:** The 500-day time series represents a single point location (`IN_TELANGANA_HYDERABAD`).
3. **Synthetic Climatology:** True monsoon extremes (e.g. 250 mm Mumbai deluge) were simulated using Gamma distributions rather than historical radar rain-gauge observations.

---

## L. SIH Presentation Boundary: What is SAFE vs What is UNSAFE

### 🟢 SAFE Claims to Make in SIH Presentation:
* *"We built an end-to-end multi-model forecast blending architecture featuring a two-stage adaptive intelligence layer (heuristic reliability + supervised gradient-boosted decision trees)."*
* *"In a 500-day causal temporal stress simulation, our adaptive blending engine reduced forecast error compared to both the individual NWP models (-35.9%) and the simple ensemble average (-4.3%)."*
* *"Our system guarantees mathematical simplex invariants ($\sum w_i \equiv 1.0, w_i \ge 0$) and handles missing feeds with zero runtime errors."*
* *"We built a spatial model-weight mapping engine covering 14 Indian meteorological subdivisions that dynamically shifts trust based on lead time and orographic profiles."*
* *"Our LLM integration (Grok) is strictly constrained to qualitative forecaster briefing synthesis and never tampers with numerical weights."*

### 🔴 Claims that MUST NOT Be Made:
* ❌ *"We have validated our system on live operational NCUM feeds from NCMRWF mainframes."* (Status: `FUTURE_AUTHORIZED_INTEGRATION`).
* ❌ *"We achieved a 38.3% error reduction on real Indian monsoon data."* (Status: `INVALID_DUE_TO_SIMULATION_LEAKAGE`).
* ❌ *"We ingested 40 years of IMDAA reanalysis NetCDF files."* (Status: `ADAPTER_READY_NOT_INGESTED`).

---

**Report Authored By:** VARUNA Scientific Audit Core  
**Commit Reference:** `feat(scientific-audit): provenance classification and causal benchmark reconciliation`
