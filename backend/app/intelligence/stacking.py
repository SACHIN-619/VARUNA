"""
VARUNA Bias-Corrected Conditional Stacking (BCCS).

Why: the softmax-over-predicted-error meta-model only *re-weights* raw forecasts, so a
systematic model bias (e.g. GFS monsoon wet bias) leaks straight into the blend. Classical
multi-model post-processing (MOS / EMOS / stacking) first removes each model's conditional
bias and then learns convex combination weights. On the project's own chronological
benchmark this reduces MAE ~5-15 % vs. the simple average across seeds, versus ~1 % for the
softmax meta-model.

Method (all fits use the TRAIN split only - strictly causal):
  1. Global additive bias b_m = mean(F_m - O) and convex weights w = NNLS(F - b, O), normalised.
  2. For each (regime, lead) cell with >= min_cell samples, the same fit is computed and
     shrunk toward the global fit with factor a = n / (n + shrinkage)  (empirical-Bayes style),
     which keeps sparse cells stable.
  3. Prediction: max(0, sum_m w_m (F_m - b_m)) over the *available* models, with weights
     re-normalised when a model is missing (graceful degradation).
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from scipy.optimize import nnls

MODELS = ["NCUM", "GFS", "WRF", "AI_WEATHER"]


class BiasCorrectedStacker:
    def __init__(self, min_cell: int = 15, shrinkage: float = 40.0, models: Optional[List[str]] = None):
        self.min_cell = min_cell
        self.shrinkage = shrinkage
        self.models: List[str] = list(models) if models else list(MODELS)
        self.n_samples = 0
        self.nonnegative = True  # rainfall / wind cannot be negative; temperature can
        # Also fit per-lead cells pooled over regimes (used when the regime cell is missing). On by default for
        # live/backfill stackers (rows carry no regime); off for the synthetic benchmark, where it measured worse.
        self.lead_fallback = False
        self.global_bias = np.zeros(len(self.models))
        self.global_w = np.ones(len(self.models)) / len(self.models)
        self.cells: Dict[Tuple[str, int], Tuple[np.ndarray, np.ndarray, int]] = {}
        self.is_fitted = False

    @staticmethod
    def _fit_block(F: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        bias = (F - y[:, None]).mean(axis=0)
        w, _ = nnls(F - bias, y)
        s = w.sum()
        w = w / s if s > 0 else np.ones(F.shape[1]) / F.shape[1]
        return bias, w

    def fit(self, rows: List[Dict[str, Any]]) -> "BiasCorrectedStacker":
        """rows: [{forecasts: {model: value}, observation: float, weather_regime: str, lead_hours: int}]"""
        rows = [r for r in rows if all(r["forecasts"].get(m) is not None for m in self.models) and r.get("observation") is not None]
        if len(rows) < 10:
            return self
        F = np.array([[float(r["forecasts"][m]) for m in self.models] for r in rows])
        y = np.array([float(r["observation"]) for r in rows])
        self.n_samples = len(rows)
        self.global_bias, self.global_w = self._fit_block(F, y)
        keys = [(str(r.get("weather_regime", "NORMAL")), int(r.get("lead_hours", 48))) for r in rows]
        lead_keys = [("*", k[1]) for k in keys]
        self.cells = {}
        groups: Dict[Tuple[str, int], List[int]] = {}
        for i, (k, lk) in enumerate(zip(keys, lead_keys)):
            groups.setdefault(k, []).append(i)
            if self.lead_fallback and k[0] != "*":
                groups.setdefault(lk, []).append(i)
        for k, idx in groups.items():
            if len(idx) >= self.min_cell:
                b, w = self._fit_block(F[idx], y[idx])
                a = len(idx) / (len(idx) + self.shrinkage)
                self.cells[k] = (a * b + (1 - a) * self.global_bias, a * w + (1 - a) * self.global_w, len(idx))
        self.is_fitted = True
        return self

    def params(self, regime: str, lead_hours: int) -> Tuple[np.ndarray, np.ndarray, str]:
        cell = self.cells.get((regime, int(lead_hours)))
        if cell:
            return cell[0], cell[1], f"CELL[{regime},{lead_hours}h] n={cell[2]}"
        cell = self.cells.get(("*", int(lead_hours)))
        if cell:
            return cell[0], cell[1], f"CELL[any regime,{lead_hours}h] n={cell[2]}"
        return self.global_bias, self.global_w, "GLOBAL"

    def predict(self, forecasts: Dict[str, Optional[float]], regime: str, lead_hours: int) -> Dict[str, Any]:
        bias, w, source = self.params(regime, lead_hours)
        avail = [i for i, m in enumerate(self.models) if forecasts.get(m) is not None]
        if not avail:
            return {"value": None, "weights": {m: 0.0 for m in self.models}, "bias": {}, "source": source}
        wa = np.array([w[i] for i in avail])
        wa = wa / wa.sum() if wa.sum() > 0 else np.ones(len(avail)) / len(avail)
        corrected = np.array([float(forecasts[self.models[i]]) - bias[i] for i in avail])
        value = float(np.dot(wa, corrected))
        if self.nonnegative:
            value = max(0.0, value)
        weights = {m: 0.0 for m in self.models}
        for j, i in enumerate(avail):
            weights[self.models[i]] = round(float(wa[j]), 4)
        return {
            "value": round(value, 2),
            "weights": weights,
            "bias": {self.models[i]: round(float(bias[i]), 2) for i in range(len(self.models))},
            "source": source,
        }


_BOOTSTRAP_STACKER: Optional[BiasCorrectedStacker] = None


def get_bootstrap_stacker() -> BiasCorrectedStacker:
    """
    Cold-start stacker fitted on the project's synthetic chronological benchmark
    (provenance: SYNTHETIC_BOOTSTRAP_PRIOR). Replace with `BiasCorrectedStacker().fit(rows)`
    on verified forecast/observation history (e.g. IMDAA / IMD gridded rainfall) in production.
    """
    global _BOOTSTRAP_STACKER
    if _BOOTSTRAP_STACKER is None:
        from app.experiments.benchmark_runner import BenchmarkExperimentRunner
        rows = BenchmarkExperimentRunner(random_seed=101).generate_chronological_dataset()
        _BOOTSTRAP_STACKER = BiasCorrectedStacker().fit(rows)
    return _BOOTSTRAP_STACKER


# Region/variable-fitted stackers built from verified history (e.g. the live ERA5 backfill).
# key: (region_id, variable, tuple(sorted(models)))
_FITTED: Dict[Tuple[str, str, Tuple[str, ...]], Tuple[BiasCorrectedStacker, str]] = {}


def register_fitted_stacker(region_id: str, variable: str, stacker: BiasCorrectedStacker, label: str) -> None:
    _FITTED[(region_id, variable, tuple(sorted(stacker.models)))] = (stacker, label)


def fit_stacker_from_rows(region_id: str, variable: str, models: List[str], rows: List[Dict[str, Any]],
                          label: str, min_rows: int = 10) -> Optional[BiasCorrectedStacker]:
    """Fit on verified (forecast, observation) rows and register it. Returns None if too few complete rows."""
    st = BiasCorrectedStacker(models=models, min_cell=10, shrinkage=20.0)
    st.nonnegative = variable != "temperature"
    st.lead_fallback = True
    st.fit(rows)
    if not st.is_fitted or st.n_samples < min_rows:
        return None
    register_fitted_stacker(region_id, variable, st, f"{label} (n={st.n_samples})")
    return st


def get_stacker_for(region_id: str, variable: str, models: List[str]) -> Tuple[Optional[BiasCorrectedStacker], str]:
    """
    Pick the stacker for this model set:
      1. a stacker fitted on verified history for exactly this region/variable/model set;
      2. for the classic NCUM/GFS/WRF/AI_WEATHER rainfall set only, the synthetic bootstrap prior;
      3. otherwise None (caller falls back to ADAPTIVE_RELIABILITY and says why).
    """
    key = (region_id, variable, tuple(sorted(models)))
    if key in _FITTED:
        st, label = _FITTED[key]
        return st, label
    if set(models) <= set(MODELS) and variable in ("rainfall", "precipitation"):
        st = get_bootstrap_stacker()
        return st, "SYNTHETIC_BOOTSTRAP_PRIOR (synthetic benchmark train split)"
    return None, "NONE"
