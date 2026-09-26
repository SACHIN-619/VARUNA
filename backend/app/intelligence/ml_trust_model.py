import os
import joblib
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from sklearn.ensemble import GradientBoostingRegressor
from scipy.special import softmax
from app.intelligence.failure_memory import failure_memory

SUPPORTED_MODELS = ["NCUM", "GFS", "WRF", "AI_WEATHER"]
REGIME_MAP = {"NORMAL": 0, "HEAVY_RAINFALL": 1, "CONVECTIVE": 2, "TRANSITION_UNCERTAIN": 3}
SEASON_MAP = {"WINTER": 0, "PRE_MONSOON": 1, "SW_MONSOON": 2, "POST_MONSOON": 3, "NE_MONSOON": 4}

class MLTrustMetaModel:
    """
    Supervised Machine Learning Meta-Model for Adaptive Forecast Blending.
    Learns non-linear conditional forecast errors e_i = |F_i - O|
    as a function of multi-model spread, synoptic regime, lead time, and recent bias,
    then transforms predicted error residuals into optimal simplex weights via calibrated softmax.
    """

    def __init__(self, model_dir: str = "./data/storage/models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.estimators: Dict[str, GradientBoostingRegressor] = {}
        self.is_trained = False
        self.feature_names = []
        self._initialize_estimators()

    def _initialize_estimators(self):
        for m in SUPPORTED_MODELS:
            self.estimators[m] = GradientBoostingRegressor(
                n_estimators=60,
                max_depth=3,
                learning_rate=0.08,
                random_state=42,
                loss="squared_error"
            )

    def extract_feature_vector(
        self,
        forecasts: Dict[str, float],
        historical_skills: Dict[str, Dict[str, float]],
        recent_errors: Dict[str, float],
        context: Dict[str, Any]
    ) -> np.ndarray:
        """
        Builds a fixed-length numerical feature vector representing multi-model state and context.
        """
        f_vals = [forecasts.get(m) or 0.0 for m in SUPPORTED_MODELS]
        valid_vals = [v for v in f_vals if v is not None and v > 0]
        f_mean = float(np.mean(valid_vals)) if valid_vals else 0.0
        f_std = float(np.std(valid_vals)) if len(valid_vals) > 1 else 0.0
        f_range = float(np.max(valid_vals) - np.min(valid_vals)) if valid_vals else 0.0

        hist_maes = [historical_skills.get(m, {}).get("MAE", 15.0) for m in SUPPORTED_MODELS]
        hist_biases = [historical_skills.get(m, {}).get("BIAS", 0.0) for m in SUPPORTED_MODELS]
        rec_errs = [recent_errors.get(m, 0.0) for m in SUPPORTED_MODELS]

        lead_hours = context.get("lead_hours", 48)
        regime_idx = REGIME_MAP.get(context.get("weather_regime", "NORMAL"), 0)
        season_idx = SEASON_MAP.get(context.get("season", "SW_MONSOON"), 2)

        # 4 forecasts + 3 spread metrics + 4 MAEs + 4 biases + 4 recent errs + 3 context = 22 features
        features = (
            f_vals +
            [f_mean, f_std, f_range] +
            hist_maes +
            hist_biases +
            rec_errs +
            [float(lead_hours), float(regime_idx), float(season_idx)]
        )
        return np.array(features, dtype=float)

    def fit(self, X: np.ndarray, Y_errors: Dict[str, np.ndarray]):
        """
        Trains independent gradient boosting regressors to predict expected
        error |F_i - Observation| for each forecasting source.
        """
        for m in SUPPORTED_MODELS:
            y = Y_errors[m]
            self.estimators[m].fit(X, y)
        self.is_trained = True
        self.save_model()

    def predict_weights(
        self,
        forecasts: Dict[str, float],
        historical_skills: Dict[str, Dict[str, float]],
        recent_errors: Dict[str, float],
        context: Dict[str, Any],
        temperature: float = 12.0
    ) -> List[Dict[str, Any]]:
        """
        Predicts conditional model error, applies softmax temperature gating,
        and enforces simplex constraints (w_i >= 0, sum(w_i) == 1.0).
        """
        active_models = [m for m, v in forecasts.items() if v is not None and not failure_memory.is_model_disabled(m)]

        if not active_models:
            return [{"model_id": m, "weight": 0.25, "status": "FALLBACK"} for m in SUPPORTED_MODELS]

        # If not trained yet, gracefully load or fit fallback
        if not self.is_trained:
            loaded = self.load_model()
            if not loaded:
                self._train_default_bootstrap_model()

        X_vec = self.extract_feature_vector(forecasts, historical_skills, recent_errors, context).reshape(1, -1)

        predicted_errors = {}
        for m in SUPPORTED_MODELS:
            if m in active_models:
                pred_err = float(self.estimators[m].predict(X_vec)[0])
                # Account for any injected operational bias
                injected = failure_memory.get_injected_bias(m)
                pred_err += abs(injected)
                predicted_errors[m] = max(1.0, pred_err)
            else:
                predicted_errors[m] = 1e6  # effectively zero weight in softmax

        # Softmax transformation: lower error -> higher weight
        # logit_i = -predicted_error_i / temperature
        logits = np.array([-predicted_errors[m] / temperature for m in SUPPORTED_MODELS])
        # Mask disabled models with -inf
        for idx, m in enumerate(SUPPORTED_MODELS):
            if m not in active_models:
                logits[idx] = -1e9

        weights = softmax(logits)

        # Enforce sum(w) == 1.0 exactly
        active_indices = [idx for idx, m in enumerate(SUPPORTED_MODELS) if m in active_models]
        sum_active = sum(weights[idx] for idx in active_indices)
        if sum_active > 0:
            for idx in active_indices:
                weights[idx] /= sum_active

        result = []
        for idx, m in enumerate(SUPPORTED_MODELS):
            status = "ACTIVE" if m in active_models else "EXCLUDED"
            w_val = round(float(weights[idx]), 4)
            result.append({
                "model_id": m,
                "weight": w_val,
                "raw_forecast": forecasts.get(m),
                "predicted_error_mae": round(float(predicted_errors.get(m, 0.0)), 2),
                "status": status,
                "strategy": "ADAPTIVE_ML_META_MODEL"
            })

        # Correct rounding delta
        active_items = [r for r in result if r["status"] == "ACTIVE"]
        if active_items:
            diff = 1.0 - sum(r["weight"] for r in active_items)
            if abs(diff) > 1e-6:
                max_item = max(active_items, key=lambda x: x["weight"])
                max_item["weight"] = round(max_item["weight"] + diff, 4)

        return result

    def _train_default_bootstrap_model(self):
        """Initializes a calibrated baseline ML model using meteorological physics distributions."""
        np.random.seed(42)
        N_samples = 400
        
        # Synthetic historical training feature matrix
        X_train = []
        Y_err = {m: [] for m in SUPPORTED_MODELS}

        for _ in range(N_samples):
            lead = np.random.choice([24, 48, 72])
            regime = np.random.choice([0, 1, 2, 3])  # Normal, Heavy, Convective, Transition
            season = np.random.choice([1, 2, 3])
            
            # Base true rainfall
            if regime == 1:
                obs = np.random.uniform(65.0, 140.0)
            elif regime == 2:
                obs = np.random.uniform(40.0, 100.0)
            else:
                obs = np.random.uniform(5.0, 45.0)

            # Realistic model errors with known physical tendencies:
            # NCUM: best in monsoon heavy rain (regime 1)
            err_ncum = np.random.normal(0, 8.0 if regime == 1 else 11.0 + (lead - 24)*0.05)
            # GFS: wet bias in heavy rain (+15mm)
            err_gfs = np.random.normal(12.0 if regime == 1 else 2.0, 14.0 + (lead - 24)*0.1)
            # WRF: excellent at 24h convective, higher error at 72h
            err_wrf = np.random.normal(-2.0, 7.0 if (regime == 2 and lead == 24) else 13.0 + (lead - 24)*0.12)
            # AI: good pattern, slightly smooths peaks
            err_ai = np.random.normal(-4.0 if obs > 80 else 0, 10.0 + (lead - 24)*0.04)

            f_ncum = max(0.0, obs + err_ncum)
            f_gfs = max(0.0, obs + err_gfs)
            f_wrf = max(0.0, obs + err_wrf)
            f_ai = max(0.0, obs + err_ai)

            forecasts = {"NCUM": f_ncum, "GFS": f_gfs, "WRF": f_wrf, "AI_WEATHER": f_ai}
            skills = {
                "NCUM": {"MAE": 9.5, "BIAS": 0.5},
                "GFS": {"MAE": 18.0, "BIAS": 12.0},
                "WRF": {"MAE": 11.0, "BIAS": -1.5},
                "AI_WEATHER": {"MAE": 12.5, "BIAS": -3.0}
            }
            recent = {"NCUM": abs(err_ncum)*0.5, "GFS": abs(err_gfs)*0.5, "WRF": abs(err_wrf)*0.5, "AI_WEATHER": abs(err_ai)*0.5}
            context = {"lead_hours": lead, "weather_regime": list(REGIME_MAP.keys())[regime], "season": "SW_MONSOON"}

            x_row = self.extract_feature_vector(forecasts, skills, recent, context)
            X_train.append(x_row)

            Y_err["NCUM"].append(abs(err_ncum))
            Y_err["GFS"].append(abs(err_gfs))
            Y_err["WRF"].append(abs(err_wrf))
            Y_err["AI_WEATHER"].append(abs(err_ai))

        X_mat = np.array(X_train)
        Y_dict = {m: np.array(Y_err[m]) for m in SUPPORTED_MODELS}
        self.fit(X_mat, Y_dict)

    def save_model(self):
        try:
            for m in SUPPORTED_MODELS:
                joblib.dump(self.estimators[m], os.path.join(self.model_dir, f"{m}_error_estimator.pkl"))
        except Exception:
            pass

    def load_model(self) -> bool:
        try:
            for m in SUPPORTED_MODELS:
                path = os.path.join(self.model_dir, f"{m}_error_estimator.pkl")
                if not os.path.exists(path):
                    return False
                self.estimators[m] = joblib.load(path)
            self.is_trained = True
            return True
        except Exception:
            return False

ml_trust_model = MLTrustMetaModel()
