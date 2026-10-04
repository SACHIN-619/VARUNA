"""
VARUNA Ground Truth Observations API Router.
SIH 2026 Problem Statement: SIH26081

Provides standardized ground-truth observations across:
- IMDAA 12km High-Resolution Reanalysis (Public Benchmark)
- IMD Automatic Weather Station (AWS) Surface Network
- Synthetic Stress-Test Truth Feeds
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Query, HTTPException

from app.services.observation_provider import observation_registry, ObservationRecord

router = APIRouter(prefix="/observations", tags=["Ground Truth Observations"])


@router.get("")
def get_observations(
    region_id: str = Query("IN_TELANGANA_HYDERABAD", description="Target region"),
    variable: str = Query("rainfall", description="rainfall | temperature | wind_speed"),
    source: str = Query("imdaa", description="imdaa | station | synthetic"),
    days_back: int = Query(7, ge=1, le=365)
):
    """Fetches historical ground-truth time series for model verification."""
    provider = observation_registry.get(source)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)

    records = provider.get_observations(
        region_id=region_id,
        variable=variable,
        start_time=start_time,
        end_time=end_time
    )

    return {
        "region_id": region_id,
        "variable": variable,
        "provider_id": provider.provider_id,
        "provenance_badge": provider.provenance,
        "count": len(records),
        "records": [r.model_dump() for r in records]
    }


@router.get("/latest")
def get_latest_observation(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    source: str = Query("imdaa")
):
    """Retrieves the most recent verified observation record."""
    provider = observation_registry.get(source)
    rec = provider.get_latest_observation(region_id, variable)
    if not rec:
        raise HTTPException(status_code=404, detail="Observation not available for specified region.")
    return rec.model_dump()


@router.get("/providers")
def list_observation_providers():
    """Lists registered ground truth observation sources and their provenance badges."""
    return observation_registry.list_providers()
