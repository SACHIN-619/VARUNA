"""Trust drift is computed from stored verification rows: recent MAE vs baseline MAE per model/region/lead."""
import uuid
from datetime import datetime, timedelta

from app.models.verification import VerificationResult

REGION = "IN_TELANGANA_DECCAN"


def _rows(model, errors, start):
    out = []
    for i, e in enumerate(errors):
        out.append(VerificationResult(
            id=str(uuid.uuid4()), region_id=REGION, variable="wind_speed", lead_hours=96, model_id=model,
            method="INDIVIDUAL_MODEL", metric="MAE", forecast_value=10.0 + e, observed_value=10.0, score=e,
            evaluation_window="TEST_DRIFT", verification_time=start + timedelta(days=i)))
    return out


def test_drift_flags_degrading_and_stable(client, db_session):
    tag = uuid.uuid4().hex[:6]
    start = datetime(2026, 1, 1)
    db_session.query(VerificationResult).filter(VerificationResult.evaluation_window == "TEST_DRIFT").delete()
    db_session.add_all(_rows("GFS", [1.0] * 10 + [4.0] * 7, start)          # recent errors 4× the baseline
                       + _rows("NCUM", [1.0] * 10 + [1.1] * 7, start)      # unchanged
                       + _rows("WRF", [1.0] * 5, start))                    # too little history
    db_session.commit()
    r = client.get("/api/verification/drift", params={"variable": "wind_speed", "region_id": REGION})
    assert r.status_code == 200, tag
    items = {(i["model_id"], i["lead_hours"]): i for i in r.json()["items"] if i["references"] == ["TEST_DRIFT"]}
    gfs, ncum, wrf = items[("GFS", 96)], items[("NCUM", 96)], items[("WRF", 96)]
    assert gfs["status"] == "DEGRADING" and gfs["baseline_mae"] == 1.0 and gfs["recent_mae"] == 4.0
    assert gfs["recent_bias"] == 4.0
    assert ncum["status"] == "STABLE"
    assert wrf["status"] == "INSUFFICIENT_HISTORY" and wrf["needed"] == 14
    db_session.query(VerificationResult).filter(VerificationResult.evaluation_window == "TEST_DRIFT").delete()
    db_session.commit()
