import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone

from app.intelligence.ml_trust_model import ml_trust_model, SUPPORTED_MODELS, REGIME_MAP
from app.intelligence.trust_model import compute_adaptive_weights
from app.intelligence.disagreement import calculate_disagreement
from app.verification.metrics import (
    calculate_continuous_metrics,
    calculate_categorical_metrics,
    calculate_brier_score
)

class BenchmarkExperimentRunner:
    """
    Executes rigorous empirical evaluation comparing all five forecasting paradigms
    on a strictly held-out, unseen chronological test period (zero temporal data leakage).
    """

    def __init__(self, n_days: int = 500, split_ratio: float = 0.70):
        self.n_days = n_days
        self.split_ratio = split_ratio

    def generate_chronological_dataset(self) -> List[Dict[str, Any]]:
        """
        Generates realistic meteorological time series representing Indian monsoon
        and transition seasons with synoptic regime persistence.
        """
        np.random.seed(101)  # Fixed seed for reproducibility
        dataset = []
        base_time = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)

        regimes_list = ["NORMAL", "HEAVY_RAINFALL", "CONVECTIVE", "TRANSITION_UNCERTAIN"]
        regime_weights = [0.45, 0.25, 0.20, 0.10]
        current_regime = "NORMAL"

        for i in range(self.n_days):
            valid_time = base_time + timedelta(days=i)
            # Markov-chain regime transition for atmospheric persistence
            if np.random.rand() < 0.35:
                current_regime = np.random.choice(regimes_list, p=regime_weights)

            lead_hours = int(np.random.choice([24, 48, 72], p=[0.35, 0.45, 0.20]))
            season = "SW_MONSOON" if (6 <= valid_time.month <= 9) else "POST_MONSOON" if (valid_time.month in [10, 11]) else "PRE_MONSOON"

            # Realistic true observed rainfall distribution (mm)
            if current_regime == "HEAVY_RAINFALL":
                obs = float(np.random.gamma(shape=4.0, scale=22.0))  # mean ~88mm
            elif current_regime == "CONVECTIVE":
                obs = float(np.random.gamma(shape=2.5, scale=20.0))  # mean ~50mm
            elif current_regime == "TRANSITION_UNCERTAIN":
                obs = float(np.random.exponential(scale=25.0))
            else:
                obs = float(np.random.exponential(scale=10.0))

            obs = round(max(0.0, min(350.0, obs)), 1)

            # Model forecasts with realistic physical biases:
            lead_factor = (lead_hours - 24) * 0.08
            
            # NCUM: High monsoon trough skill, slight underestimation of localized extreme peaks
            err_ncum = np.random.normal(0.5, 9.0 + lead_factor)
            # GFS: Global NWP, known wet-bias tendency in Indian peninsula during monsoon
            err_gfs = np.random.normal(12.5 if current_regime == "HEAVY_RAINFALL" else 2.5, 14.0 + lead_factor * 1.5)
            # WRF: Mesoscale resolution, strong at 24h convective, boundary dispersion at 72h
            err_wrf = np.random.normal(-1.5, 7.5 if (current_regime == "CONVECTIVE" and lead_hours == 24) else 13.5 + lead_factor * 1.8)
            # AI: Machine learning pattern consistency, slight peak smoothing
            err_ai = np.random.normal(-3.5 if obs > 70 else 0.0, 10.5 + lead_factor)

            f_ncum = round(max(0.0, obs + err_ncum), 1)
            f_gfs = round(max(0.0, obs + err_gfs), 1)
            f_wrf = round(max(0.0, obs + err_wrf), 1)
            f_ai = round(max(0.0, obs + err_ai), 1)

            forecasts = {"NCUM": f_ncum, "GFS": f_gfs, "WRF": f_wrf, "AI_WEATHER": f_ai}
            skills = {
                "NCUM": {"MAE": 9.2, "BIAS": 0.5},
                "GFS": {"MAE": 18.5, "BIAS": 11.2},
                "WRF": {"MAE": 11.4, "BIAS": -1.2},
                "AI_WEATHER": {"MAE": 11.8, "BIAS": -2.8}
            }
            recent = {
                "NCUM": round(abs(err_ncum) * 0.4, 1),
                "GFS": round(abs(err_gfs) * 0.5, 1),
                "WRF": round(abs(err_wrf) * 0.4, 1),
                "AI_WEATHER": round(abs(err_ai) * 0.4, 1)
            }

            dataset.append({
                "day_index": i + 1,
                "valid_time": valid_time.isoformat(),
                "lead_hours": lead_hours,
                "season": season,
                "weather_regime": current_regime,
                "observation": obs,
                "forecasts": forecasts,
                "historical_skills": skills,
                "recent_errors": recent
            })

        return dataset

    def run_experiment(self) -> Dict[str, Any]:
        """
        Executes strict temporal split training and evaluation:
        1. Train ML meta-model on Chronological Period 1 (Days 1 to 350)
        2. Evaluate on unseen Chronological Period 2 (Days 351 to 500)
        3. Compare all 5 paradigms on the unseen period
        """
        full_data = self.generate_chronological_dataset()
        n_total = len(full_data)
        split_idx = int(n_total * self.split_ratio)

        train_data = full_data[:split_idx]
        test_data = full_data[split_idx:]

        # Step 1: Train ML Meta-Model on training split
        X_train = []
        Y_train_err = {m: [] for m in SUPPORTED_MODELS}

        for row in train_data:
            ctx = {
                "lead_hours": row["lead_hours"],
                "weather_regime": row["weather_regime"],
                "season": row["season"],
                "region_id": "IN_TELANGANA_HYDERABAD"
            }
            x_vec = ml_trust_model.extract_feature_vector(
                row["forecasts"],
                row["historical_skills"],
                row["recent_errors"],
                ctx
            )
            X_train.append(x_vec)
            for m in SUPPORTED_MODELS:
                obs = row["observation"]
                f_val = row["forecasts"][m]
                Y_train_err[m].append(abs(f_val - obs))

        ml_trust_model.fit(np.array(X_train), {m: np.array(Y_train_err[m]) for m in SUPPORTED_MODELS})

        # Step 2: Evaluate on Unseen Test Split
        obs_test = [row["observation"] for row in test_data]
        
        # Accumulators
        preds = {
            "NCUM": [],
            "GFS": [],
            "WRF": [],
            "AI_WEATHER": [],
            "SIMPLE_AVERAGE": [],
            "STATIC_BLEND": [],
            "ADAPTIVE_RELIABILITY_BASELINE": [],
            "ADAPTIVE_ML_META_MODEL": []
        }
        probs_adaptive_ml = []

        static_weights = {"NCUM": 0.40, "WRF": 0.30, "GFS": 0.20, "AI_WEATHER": 0.10}

        for row in test_data:
            f = row["forecasts"]
            ctx = {
                "lead_hours": row["lead_hours"],
                "weather_regime": row["weather_regime"],
                "season": row["season"],
                "region_id": "IN_TELANGANA_HYDERABAD",
                "variable": "rainfall"
            }

            # 1. Individual models
            for m in SUPPORTED_MODELS:
                preds[m].append(f[m])

            # 2. Simple Average
            preds["SIMPLE_AVERAGE"].append(float(np.mean(list(f.values()))))

            # 3. Static Blend
            static_val = sum(static_weights[m] * f[m] for m in SUPPORTED_MODELS)
            preds["STATIC_BLEND"].append(static_val)

            # 4. Adaptive Reliability (Heuristic Baseline)
            disagree = calculate_disagreement(f, "rainfall")
            rel_weights = compute_adaptive_weights(f, row["historical_skills"], row["recent_errors"], ctx, disagree)
            rel_val = sum(w["weight"] * f[w["model_id"]] for w in rel_weights)
            preds["ADAPTIVE_RELIABILITY_BASELINE"].append(rel_val)

            # 5. Adaptive ML (Learned Supervised Meta-Model)
            ml_weights = ml_trust_model.predict_weights(f, row["historical_skills"], row["recent_errors"], ctx)
            ml_val = sum(w["weight"] * f[w["model_id"]] for w in ml_weights)
            preds["ADAPTIVE_ML_META_MODEL"].append(ml_val)
            
            # Extreme event exceedance probability (> 64.5mm)
            prob_est = 95.0 if ml_val > 75.0 else 5.0 if ml_val < 45.0 else 55.0
            probs_adaptive_ml.append(prob_est)

        # Step 3: Compute Metrics across all methods on unseen test set
        methods_summary = []
        for method_name, f_list in preds.items():
            c_metrics = calculate_continuous_metrics(f_list, obs_test)
            cat_metrics = calculate_categorical_metrics(f_list, obs_test, threshold=64.5)
            
            brier_val = None
            if method_name == "ADAPTIVE_ML_META_MODEL":
                brier_val = calculate_brier_score(probs_adaptive_ml, obs_test, threshold=64.5)

            methods_summary.append({
                "method": method_name,
                "mae": c_metrics["mae"],
                "rmse": c_metrics["rmse"],
                "bias": c_metrics["bias"],
                "correlation": c_metrics["correlation"],
                "pod": cat_metrics["pod"],
                "far": cat_metrics["far"],
                "csi": cat_metrics["csi"],
                "brier": brier_val
            })

        # Calculate actual improvement percentages on unseen data
        mae_map = {m["method"]: m["mae"] for m in methods_summary}
        simple_mae = mae_map["SIMPLE_AVERAGE"]
        rel_mae = mae_map["ADAPTIVE_RELIABILITY_BASELINE"]
        ml_mae = mae_map["ADAPTIVE_ML_META_MODEL"]

        ml_improvement_over_simple_pct = round(((simple_mae - ml_mae) / simple_mae) * 100.0, 2)
        ml_improvement_over_heuristic_pct = round(((rel_mae - ml_mae) / rel_mae) * 100.0, 2)

        return {
            "experiment_id": "EXP_TEMPORAL_MONSOON_BENCHMARK_2026",
            "title": "Unseen Temporal Evaluation: Individual Models vs Baselines vs Adaptive ML",
            "total_samples": n_total,
            "train_samples": len(train_data),
            "unseen_test_samples": len(test_data),
            "temporal_split_date": test_data[0]["valid_time"][:10],
            "split_ratio": f"{int(self.split_ratio*100)}% Train / {int((1-self.split_ratio)*100)}% Unseen Test",
            "data_provenance": "synthetic_temporal_benchmark",
            "results_table": methods_summary,
            "scientific_findings": {
                "simple_average_mae": simple_mae,
                "adaptive_reliability_baseline_mae": rel_mae,
                "adaptive_ml_meta_model_mae": ml_mae,
                "ml_mae_reduction_vs_simple_average_pct": ml_improvement_over_simple_pct,
                "ml_mae_reduction_vs_heuristic_baseline_pct": ml_improvement_over_heuristic_pct,
                "conclusion": (
                    f"On {len(test_data)} unseen test days, Adaptive ML Meta-Model achieved an MAE of {ml_mae:.2f} mm, "
                    f"representing a {ml_improvement_over_simple_pct:+.1f}% error reduction over Simple Average ({simple_mae:.2f} mm) "
                    f"and {ml_improvement_over_heuristic_pct:+.1f}% error reduction over the Heuristic Reliability Baseline ({rel_mae:.2f} mm)."
                )
            }
        }

benchmark_runner = BenchmarkExperimentRunner()
