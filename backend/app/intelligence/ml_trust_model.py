import os
import json
import joblib
import numpy as np
from datetime import datetime, timezone
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
    as a function of multi-model spread, synoptic regime, lead time, and prior historical skill,
    then transforms predicted error residuals into optimal simplex weights via calibrated softmax.
    """

    def __init__(self, model_dir: Optional[str] = None):
        from app.core.config import settings
        self.model_dir = model_dir or settings.ML_MODEL_PATH
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
        Preserves 0.0 mm rainfall forecasts as valid zero observations.
        """
        f_vals = [forecasts.get(m) for m in SUPPORTED_MODELS]
        valid_vals = [v for v in f_vals if v is not None and isinstance(v, (int, float)) and v >= 0.0]
        
        f_mean = float(np.mean(valid_vals)) if valid_vals else 0.0
        f_std = float(np.std(valid_vals)) if len(valid_vals) > 1 else 0.0
        f_range = float(np.max(valid_vals) - np.min(valid_vals)) if valid_vals else 0.0

        hist_maes = [historical_skills.get(m, {}).get("MAE", 15.0) for m in SUPPORTED_MODELS]
        hist_biases = [historical_skills.get(m, {}).get("BIAS", 0.0) for m in SUPPORTED_MODELS]
        rec_errs = [recent_errors.get(m, 0.0) for m in SUPPORTED_MODELS]

        lead_hours = context.get("lead_hours", 48)
        regime_idx = REGIME_MAP.get(context.get("weather_regime", "NORMAL"), 0)
        season_idx = SEASON_MAP.get(context.get("season", "SW_MONSOON"), 2)

        # Vector format: 4 forecasts + 3 spread + 4 MAEs + 4 biases + 4 recent errs + 3 context = 22 features
        f_clean_vals = [float(v) if v is not None else 0.0 for v in f_vals]
        features = (
            f_clean_vals +
            [f_mean, f_std, f_range] +
            hist_maes +
            hist_biases +
            rec_errs +
            [float(lead_hours), float(regime_idx), float(season_idx)]
        )
        return np.array(features, dtype=np.float32)

    def fit(
        self,
        X_train: np.ndarray,
        Y_train_dict: Dict[str, np.ndarray],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Trains independent GBR estimators per supported model.
        """
        for m in SUPPORTED_MODELS:
            if m in Y_train_dict and len(Y_train_dict[m]) == len(X_train):
                self.estimators[m].fit(X_train, Y_train_dict[m])
        self.is_trained = True
        self.save_model(metadata)

    def fit_on_real_records(
        self,
        dataset_records: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Fits ML meta-model on real observation-verified forecast records.
        SCIENTIFIC SAFETY INVARIANT: Strictly prevents target leakage by constructing
        features from prior window (t - k to t - 1) before evaluating target at t.
        """
        if not dataset_records:
            return

        X_train = []
        Y_err = {m: [] for m in SUPPORTED_MODELS}

        running_history: Dict[str, List[float]] = {m: [] for m in SUPPORTED_MODELS}

        for rec in dataset_records:
            forecasts = rec.get("forecasts", {})
            actual_errors = rec.get("actual_errors", {})

            # Construct PRIOR skills and recent errors from past windows (t-1), NOT current target t
            skills = {}
            recent = {}
            for m in SUPPORTED_MODELS:
                history_m = running_history[m]
                if history_m:
                    skills[m] = {"MAE": float(np.mean(history_m)), "BIAS": float(np.mean(history_m) * 0.1)}
                    recent[m] = float(np.mean(history_m[-3:]))
                else:
                    skills[m] = {"MAE": 12.0, "BIAS": 0.0}
                    recent[m] = 6.0

            context = {
                "lead_hours": rec.get("lead_hours", 48),
                "weather_regime": rec.get("weather_regime", "NORMAL"),
                "season": rec.get("season", "SW_MONSOON")
            }

            x_vec = self.extract_feature_vector(forecasts, skills, recent, context)
            X_train.append(x_vec)

            for m in SUPPORTED_MODELS:
                target_err = actual_errors.get(m, 10.0)
                Y_err[m].append(target_err)
                # Append to running history for future records
                running_history[m].append(target_err)

        X_mat = np.array(X_train)
        Y_dict = {m: np.array(Y_err[m]) for m in SUPPORTED_MODELS}

        meta = {
            "version": "v2.0.0-real-data",
            "samples": len(dataset_records),
            "provenance": metadata.get("provenance", "PUBLIC_BENCHMARK") if metadata else "PUBLIC_BENCHMARK"
        }
        self.fit(X_mat, Y_dict, metadata=meta)

    BOOTSTRAP_VERSION = "v2.0.0-bootstrap-causal"

    @staticmethod
    def _bootstrap_error_params(model: str, regime: str, lead: int) -> Tuple[float, float]:
        """
        Documented, physically-motivated conditional error model (bias, sigma) in mm/24h.
        Encodes the README claims so the bootstrap meta-model actually *learns* them:
          NCUM  - strongest in monsoon trough / heavy rain, moderate lead-time growth
          GFS   - wet bias in heavy-rain regimes
          WRF   - best at 24 h in convective / orographic rain, fastest error growth with lead
          AI    - slowest error growth with lead, peak-dampening (dry bias) in heavy / convective rain
        """
        dl = max(0, lead - 24)
        heavy = regime in ("HEAVY_RAINFALL", "CONVECTIVE")
        if model == "NCUM":
            return (0.5, (6.5 if regime == "HEAVY_RAINFALL" else 8.5) + 0.06 * dl)
        if model == "GFS":
            return ((11.0 if regime == "HEAVY_RAINFALL" else 2.5), 10.5 + 0.08 * dl)
        if model == "WRF":
            return (-1.0, (5.5 if heavy else 8.0) + 0.16 * dl)
        # AI_WEATHER
        return ((-4.0 if heavy else -0.5), (9.0 if regime == "CONVECTIVE" else 8.0) + 0.025 * dl)

    def _train_default_bootstrap_model(self, N_samples: int = 3000):
        """
        Cold-start synthetic bootstrap meta-model (explicit SYNTHETIC_BOOTSTRAP_PRIOR provenance).

        BUGFIX (target leakage): the previous version set each model's `recent_error`
        feature to 0.5 * |current target error|, so the regressor simply learned
        `error = 2 * recent_error` and ignored lead time, regime and season. Weights
        therefore never changed when the forecaster changed lead time or regime.
        Recent errors are now the mean of 3 *independent prior* draws from the same
        conditional distribution (strictly causal), and historical MAE is the
        analytic expectation plus sampling noise.
        """
        rng = np.random.default_rng(42)
        regimes = list(REGIME_MAP.keys())
        X_train = []
        Y_err = {m: [] for m in SUPPORTED_MODELS}

        for _ in range(N_samples):
            lead = int(rng.choice([24, 48, 72]))
            regime = regimes[int(rng.integers(0, len(regimes)))]
            obs = float(rng.gamma(1.6, 22.0 if regime == "HEAVY_RAINFALL" else 9.0))
            intensity = 0.55 + min(obs, 150.0) / 70.0  # errors scale with rain intensity

            forecasts, skills, recent, cur_err = {}, {}, {}, {}
            for m in SUPPORTED_MODELS:
                bias, sigma = self._bootstrap_error_params(m, regime, lead)
                sig = sigma * intensity
                e = float(rng.normal(bias * intensity, sig))
                f = max(0.0, obs + e)
                cur_err[m] = abs(f - obs)
                forecasts[m] = f
                prior = np.abs(rng.normal(bias * intensity, sig, size=3))
                recent[m] = float(prior.mean())
                exp_mae = abs(bias) + sigma * 0.798  # E|N(0, s)| = s*sqrt(2/pi)
                skills[m] = {"MAE": float(exp_mae * rng.uniform(0.85, 1.15)), "BIAS": float(bias)}

            context = {"lead_hours": lead, "weather_regime": regime, "season": "SW_MONSOON"}
            X_train.append(self.extract_feature_vector(forecasts, skills, recent, context))
            for m in SUPPORTED_MODELS:
                Y_err[m].append(cur_err[m])

        X_mat = np.array(X_train)
        Y_dict = {m: np.array(Y_err[m]) for m in SUPPORTED_MODELS}
        self.fit(X_mat, Y_dict, metadata={
            "version": self.BOOTSTRAP_VERSION,
            "samples": N_samples,
            "provenance": "SYNTHETIC_BOOTSTRAP_PRIOR"
        })

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

        if not self.is_trained:
            loaded = self.load_model()
            if not loaded:
                self._train_default_bootstrap_model()

        X_vec = self.extract_feature_vector(forecasts, historical_skills, recent_errors, context).reshape(1, -1)

        predicted_errors = {}
        for m in SUPPORTED_MODELS:
            if m in active_models:
                pred_err = float(self.estimators[m].predict(X_vec)[0])
                injected = failure_memory.get_injected_bias(m)
                pred_err += abs(injected)
                predicted_errors[m] = max(1.0, pred_err)
            else:
                predicted_errors[m] = 1e6

        # Softmax transformation: lower predicted error -> higher weight
        logits = np.array([-predicted_errors[m] / temperature for m in SUPPORTED_MODELS])
        raw_weights = softmax(logits)

        weights_list = []
        for idx, m in enumerate(SUPPORTED_MODELS):
            w = float(raw_weights[idx]) if m in active_models else 0.0
            status = "ACTIVE" if m in active_models else "EXCLUDED"
            weights_list.append({
                "model_id": m,
                "weight": round(w, 4),
                "predicted_error": round(predicted_errors[m], 2),
                "status": status
            })

        # Exact normalization enforcement
        active_items = [item for item in weights_list if item["status"] == "ACTIVE"]
        if active_items:
            current_sum = sum(item["weight"] for item in active_items)
            if current_sum > 0:
                for item in active_items:
                    item["weight"] = round(item["weight"] / current_sum, 4)
                diff = round(1.0 - sum(item["weight"] for item in active_items), 4)
                if abs(diff) > 1e-5:
                    max_item = max(active_items, key=lambda x: x["weight"])
                    max_item["weight"] = round(max_item["weight"] + diff, 4)

        return weights_list

    def save_model(self, metadata: Optional[Dict[str, Any]] = None):
        """Saves estimator binary artifacts and structured manifest."""
        try:
            for m in SUPPORTED_MODELS:
                joblib.dump(self.estimators[m], os.path.join(self.model_dir, f"{m}_error_estimator.pkl"))
            
            manifest = {
                "version": metadata.get("version", "v1.0.0") if metadata else "v1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "models": SUPPORTED_MODELS,
                "feature_count": 22,
                "feature_names": [
                    "forecast_NCUM", "forecast_GFS", "forecast_WRF", "forecast_AI",
                    "multi_model_mean", "multi_model_std", "multi_model_range",
                    "historical_mae_NCUM", "historical_mae_GFS", "historical_mae_WRF", "historical_mae_AI",
                    "historical_bias_NCUM", "historical_bias_GFS", "historical_bias_WRF", "historical_bias_AI",
                    "recent_error_NCUM", "recent_error_GFS", "recent_error_WRF", "recent_error_AI",
                    "lead_hours", "regime_index", "season_index"
                ],
                "sample_count": metadata.get("samples", 0) if metadata else 0,
                "provenance": metadata.get("provenance", "SYNTHETIC_BOOTSTRAP_PRIOR") if metadata else "SYNTHETIC_BOOTSTRAP_PRIOR"
            }
            with open(os.path.join(self.model_dir, "artifact_manifest.json"), "w") as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass

    def load_model(self) -> bool:
        try:
            manifest_path = os.path.join(self.model_dir, "artifact_manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                # Stale (leaky) bootstrap artifacts are discarded and retrained on first use
                if manifest.get("provenance") == "SYNTHETIC_BOOTSTRAP_PRIOR" and manifest.get("version") != self.BOOTSTRAP_VERSION:
                    return False
            for m in SUPPORTED_MODELS:
                path = os.path.join(self.model_dir, f"{m}_error_estimator.pkl")
                if not os.path.exists(path):
                    return False
                self.estimators[m] = joblib.load(path)
            self.is_trained = True
            return True
        except Exception:
            return False

    def get_model_metadata(self) -> Dict[str, Any]:
        manifest_path = os.path.join(self.model_dir, "artifact_manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "v1.0.0-bootstrap",
            "is_trained": self.is_trained,
            "models": SUPPORTED_MODELS,
            "feature_count": 22,
            "provenance": "SYNTHETIC_BOOTSTRAP_PRIOR"
        }

ml_trust_model = MLTrustMetaModel()
