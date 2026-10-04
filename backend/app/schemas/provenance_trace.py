"""
VARUNA Scientific Provenance & Forecast Trace Schema.
SIH 2026 Problem Statement: SIH26081

Exposes a complete, auditable ForecastTrace object for duty-forecasters and control-room UI:
ForecastTrace
 ├── Sources (raw feeds, original units, resolutions, authorization)
 ├── Harmonization (unit conversions, spatial resampling, physical bounds)
 ├── Context (canonical ContextVector, regime, synoptic features)
 ├── Trust Weights (Level 1 baseline / Level 2 ML meta-model, status, sum=1.0)
 ├── Disagreement (std_dev, weighted_spread, range, variance)
 ├── Fusion (fused value, simple average, static blend, status)
 ├── Uncertainty (epistemic confidence, exceedance indicator, margin)
 ├── ML Artifact (version, training sample count, provenance)
 └── Verification History (recent MAE, sample count, evaluation window)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ModelSourceTrace(BaseModel):
    model_id: str
    raw_value: Optional[float]
    canonical_value: Optional[float]
    unit: str
    resolution: str
    source_agency: str
    provenance_badge: str
    authorization_status: str
    is_available: bool


class HarmonizationTrace(BaseModel):
    unit_conversions_applied: List[str]
    spatial_resampling_method: str
    target_resolution: str
    physical_bounds_status: str


class ForecastTrace(BaseModel):
    """
    Comprehensive, end-to-end scientific provenance trace.
    Guarantees every output is explainable, reproducible, and verifiable.
    """
    trace_id: str = Field(..., description="Unique audit trace identifier")
    forecast_cycle_id: str
    generated_at: datetime
    region_id: str
    variable: str
    lead_hours: int
    data_provenance_badge: str = Field(..., description="PUBLIC_BENCHMARK | SYNTHETIC_STRESS_TEST | AUTHORIZED_OPERATIONAL_FEED")
    
    # 1. Sources
    sources: List[ModelSourceTrace]
    
    # 2. Harmonization
    harmonization: HarmonizationTrace
    
    # 3. Context
    context: Dict[str, Any]
    
    # 4. Trust Weights
    trust_weights: List[Dict[str, Any]]
    blending_strategy: str = Field(..., description="ADAPTIVE_ML_META_MODEL | ADAPTIVE_RELIABILITY_BASELINE")
    weights_sum: float
    
    # 5. Disagreement
    disagreement: Dict[str, Any]
    
    # 6. Fusion
    fusion: Dict[str, Any]
    
    # 7. Uncertainty
    uncertainty: Dict[str, Any]
    
    # 8. ML Model Metadata
    ml_model_metadata: Dict[str, Any]
    
    # 9. Verification Context
    verification_history: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
