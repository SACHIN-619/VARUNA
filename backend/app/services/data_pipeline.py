"""
VARUNA Scientific Data Pipeline & Verification Engine.
Orchestrates the closed-loop meteorological learning cycle:
Forecasts -> Harmonization -> Fusion -> Observation Matching -> Verification -> Dynamic Skill Update
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import numpy as np

from app.models.skill import ModelSkill
from app.models.verification import VerificationResult
from app.models.forecast import ForecastValue
from app.services.observation_provider import observation_registry, ObservationRecord
from app.verification.metrics import (
    calculate_continuous_metrics,
    calculate_categorical_metrics,
    calculate_brier_score
)
from app.services.canonical_pipeline import canonical_pipeline, CanonicalPipelineOrchestrator


class DataPipelineService:
    """
    Coordinates ingestion of forecast-observation pairs and automated
    model skill recalibration without fabricated observational fallbacks.
    """

    def __init__(self, observation_source: str = "imdaa"):
        self.obs_source = observation_source
        self.canonical = canonical_pipeline

    def run_canonical_cycle(
        self,
        db: Session,
        region_id: str,
        variable: str,
        lead_hours: int,
        model_forecasts: Dict[str, float],
        ground_truth: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes the full 14-stage VARUNA pipeline end-to-end.
        """
        return self.canonical.execute_pipeline(
            db=db,
            region_id=region_id,
            variable=variable,
            lead_hours=lead_hours,
            raw_forecasts=model_forecasts,
            observation_val=ground_truth
        )

    def ingest_and_verify_cycle(
        self,
        db: Session,
        region_id: str,
        variable: str,
        lead_hours: int,
        model_forecasts: Dict[str, float],
        fused_forecast: float,
        valid_time: datetime,
        ground_truth: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes real-time verification matching against verified ground truth.
        Computes forecast errors and persists verification audit trail.
        """
        # 1. Fetch observation if not directly provided
        if ground_truth is None:
            obs_provider = observation_registry.get(self.obs_source)
            latest_obs = obs_provider.get_latest_observation(region_id, variable) if obs_provider else None
            
            if latest_obs and latest_obs.observed_value is not None:
                obs_val = latest_obs.observed_value
                obs_provenance = latest_obs.data_provenance or "PUBLIC_IMDAA_REANALYSIS"
            else:
                # SCIENTIFIC SAFETY INVARIANT: Never substitute a fabricated observation fallback!
                return {
                    "status": "NOT_VERIFIED",
                    "reason": "OBSERVATION_UNAVAILABLE",
                    "region_id": region_id,
                    "variable": variable,
                    "lead_hours": lead_hours,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }
        else:
            obs_val = ground_truth
            obs_provenance = "GROUND_TRUTH_VERIFIED"

        # 2. Compute errors for each source
        cycle_errors = {}
        for m_id, f_val in model_forecasts.items():
            err = round(f_val - obs_val, 2)
            abs_err = round(abs(err), 2)
            cycle_errors[m_id] = {"error": err, "abs_error": abs_err}

            # Persist individual model verification row
            db.add(VerificationResult(
                region_id=region_id,
                variable=variable,
                lead_hours=lead_hours,
                model_id=m_id,
                method="INDIVIDUAL_MODEL",
                metric="MAE",
                forecast_value=f_val,
                observed_value=obs_val,
                score=abs_err,
                evaluation_window="operational_cycle",
                verification_time=datetime.now(timezone.utc)
            ))

        # 3. Compute error for fused forecast
        fused_err = round(fused_forecast - obs_val, 2)
        fused_abs_err = round(abs(fused_err), 2)
        cycle_errors["VARUNA_FUSED"] = {"error": fused_err, "abs_error": fused_abs_err}

        db.add(VerificationResult(
            region_id=region_id,
            variable=variable,
            lead_hours=lead_hours,
            model_id=None,
            method="ADAPTIVE_ML_FUSION",
            metric="MAE",
            forecast_value=fused_forecast,
            observed_value=obs_val,
            score=fused_abs_err,
            evaluation_window="operational_cycle",
            verification_time=datetime.now(timezone.utc)
        ))

        db.commit()

        return {
            "status": "VERIFIED",
            "region_id": region_id,
            "variable": variable,
            "lead_hours": lead_hours,
            "observation_value": obs_val,
            "observation_provenance": obs_provenance,
            "forecast_errors": cycle_errors,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }

    def update_model_skills_from_history(
        self,
        db: Session,
        region_id: str,
        variable: str = "rainfall",
        lead_hours: int = 48,
        season: str = "SW_MONSOON",
        weather_regime: str = "HEAVY_RAINFALL"
    ) -> Dict[str, Any]:
        """
        Closed-loop skill update:
        Aggregates verification records and recalculates MAE and Bias for each model,
        updating the ModelSkill database table.
        """
        found = [r[0] for r in db.query(VerificationResult.model_id).filter(
            VerificationResult.region_id == region_id, VerificationResult.variable == variable,
            VerificationResult.lead_hours == lead_hours, VerificationResult.model_id.isnot(None)).distinct().all()]
        models = sorted(set(found) | {"NCUM", "GFS", "WRF", "AI_WEATHER"})
        updated_skills = {}

        for m_id in models:
            records = db.query(VerificationResult).filter(
                VerificationResult.region_id == region_id,
                VerificationResult.variable == variable,
                VerificationResult.lead_hours == lead_hours,
                VerificationResult.model_id == m_id,
                VerificationResult.metric == "MAE",
                VerificationResult.method == "INDIVIDUAL_MODEL",
            ).all()

            if records:
                mae_score = round(float(np.mean([r.score for r in records])), 2)
                # `is not None` (not truthiness): 0.0 mm forecasts/observations are valid and
                # very common for rainfall; excluding them biased the BIAS estimate wet.
                diffs = [(r.forecast_value - r.observed_value) for r in records
                         if r.forecast_value is not None and r.observed_value is not None]
                bias_score = round(float(np.mean(diffs)), 2) if diffs else 0.0
                sample_count = len(records)
                provenance_type = "OBSERVATION_DERIVED"
            else:
                # Cold-start baseline values (clearly marked as BOOTSTRAP_PRIOR, sample_count = 0)
                mae_score = 9.2 if m_id == "NCUM" else 18.5 if m_id == "GFS" else 11.4 if m_id == "WRF" else 11.8
                bias_score = 0.5 if m_id == "NCUM" else 11.2 if m_id == "GFS" else -1.2 if m_id == "WRF" else -2.8
                sample_count = 0
                provenance_type = "BOOTSTRAP_PRIOR"

            if sample_count == 0:
                # Never overwrite DB skill with a bootstrap prior; just report it
                updated_skills[m_id] = {"mae": mae_score, "bias": bias_score, "sample_count": 0,
                                        "provenance_type": provenance_type}
                continue

            # Update or create ModelSkill record in DB
            skill_entry = db.query(ModelSkill).filter(
                ModelSkill.model_id == m_id,
                ModelSkill.region_id == region_id,
                ModelSkill.variable == variable,
                ModelSkill.lead_hours == lead_hours,
                ModelSkill.season == season,
                ModelSkill.weather_regime == weather_regime,
                ModelSkill.metric == "MAE"
            ).first()

            if skill_entry:
                skill_entry.value = mae_score
                skill_entry.sample_count = sample_count
                skill_entry.evaluation_period = "continuous_verification_pipeline"
                skill_entry.updated_at = datetime.now(timezone.utc)
            else:
                db.add(ModelSkill(
                    model_id=m_id,
                    region_id=region_id,
                    variable=variable,
                    lead_hours=lead_hours,
                    season=season,
                    weather_regime=weather_regime,
                    metric="MAE",
                    value=mae_score,
                    sample_count=sample_count,
                    evaluation_period="continuous_verification_pipeline"
                ))

            updated_skills[m_id] = {
                "mae": mae_score,
                "bias": bias_score,
                "sample_count": sample_count,
                "provenance_type": provenance_type
            }

        db.commit()

        return {
            "status": "SUCCESS",
            "region_id": region_id,
            "variable": variable,
            "lead_hours": lead_hours,
            "season": season,
            "weather_regime": weather_regime,
            "updated_model_skills": updated_skills,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


data_pipeline = DataPipelineService()
