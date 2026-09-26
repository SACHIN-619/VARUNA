from fastapi import APIRouter, Query
from app.demo.scenario_generator import scenario_generator

router = APIRouter(prefix="/what-changed", tags=["Cycle Diagnostics"])

@router.get("")
def get_cycle_changes(
    region_id: str = Query("IN_TELANGANA_HYDERABAD"),
    variable: str = Query("rainfall"),
    lead_hours: int = Query(48)
):
    """
    Compares the current forecast cycle against the previous cycle.
    Returns delta in forecast intensity, probability shift, and primary synoptic driver.
    """
    res = scenario_generator.execute_pipeline(
        custom_context={"region_id": region_id, "variable": variable, "lead_hours": lead_hours}
    )
    return {
        "region_id": region_id,
        "variable": variable,
        "lead_hours": lead_hours,
        "change_diagnostics": res["what_changed"]
    }
