"""
Forecast-change notifications.

Every pipeline result shown on the control room can be snapshotted. When the inputs change for the same
(region, variable, lead, source mode, strategy) stream, the new snapshot is compared with the previous one
and each rule below is evaluated with its numbers written down, so the bell can show *why* it fired:

  R1 fused value jump     |Δ| >= max(abs_threshold[variable], 25 % of previous)
  R2 alert level change   IMD colour level differs
  R3 dominant model       model with the largest weight differs
  R4 confidence change    confidence grade differs
  R5 weight shift         any model weight moved >= 15 percentage points

Snapshots are de-duplicated by a SHA-256 of the inputs, so repeated page loads do not create noise.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.notification import ForecastSnapshot, Notification

ABS_THRESHOLD = {"rainfall": 10.0, "temperature": 2.0, "wind_speed": 3.0}
REL_THRESHOLD = 0.25
WEIGHT_SHIFT_PTS = 15.0
ALERT_RANK = {None: 0, "NONE": 0, "GREY": 0, "GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}

_lock = threading.Lock()


def _input_hash(pkg: Dict[str, Any], source_mode: str) -> str:
    basis = {
        "mode": source_mode,
        "forecasts": pkg["inputs"]["raw_forecasts"],
        "strategy": pkg.get("strategy"),
        "issue": pkg.get("issue_time"),
        "fused": pkg["fusion"].get("fused_value"),
    }
    return hashlib.sha256(json.dumps(basis, sort_keys=True, default=str).encode()).hexdigest()


def _dominant(weights: Dict[str, float]) -> Optional[str]:
    return max(weights, key=weights.get) if weights else None


def _sources(pkg: Dict[str, Any], received_at: str) -> List[Dict[str, Any]]:
    meta = pkg["inputs"].get("source_meta") or {}
    out = []
    for m, v in pkg["inputs"]["raw_forecasts"].items():
        sm = meta.get(m, {})
        out.append({
            "model_id": m, "value": v,
            "source": sm.get("source", "SYNTHETIC_DEMO_SCENARIO" if not meta else "UNKNOWN"),
            "provenance": sm.get("provenance", "SYNTHETIC_DEMO" if not meta else None),
            "dataset_id": sm.get("dataset_id"),
            "issue_time": sm.get("issue_time"),
            "received_at": sm.get("fetched_at") or received_at,
            "weight": pkg["trust_modeling"]["final_weights"].get(m),
        })
    return out


def evaluate_rules(prev: ForecastSnapshot, cur: ForecastSnapshot, variable: str) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    pv, cv = prev.fused_value, cur.fused_value
    if pv is not None and cv is not None:
        delta = round(cv - pv, 2)
        thr = round(max(ABS_THRESHOLD.get(variable, 5.0), REL_THRESHOLD * abs(pv)), 2)
        rules.append({
            "rule": "R1_FUSED_JUMP", "formula": "|F_now - F_prev| >= max(abs_thr, 0.25 x |F_prev|)",
            "values": {"F_prev": pv, "F_now": cv, "delta": delta, "abs_thr": ABS_THRESHOLD.get(variable, 5.0),
                       "threshold": thr},
            "computation": f"|{cv} - {pv}| = {abs(delta)} {'>=' if abs(delta) >= thr else '<'} {thr}",
            "triggered": abs(delta) >= thr,
        })
    rules.append({
        "rule": "R2_ALERT_LEVEL", "formula": "IMD level(F_now) != IMD level(F_prev)",
        "values": {"prev": prev.alert_level, "now": cur.alert_level},
        "computation": f"{prev.alert_level} -> {cur.alert_level}",
        "triggered": (prev.alert_level or "NONE") != (cur.alert_level or "NONE"),
    })
    pw, cw = prev.weights_json or {}, cur.weights_json or {}
    pd, cd = _dominant(pw), _dominant(cw)
    rules.append({
        "rule": "R3_DOMINANT_MODEL", "formula": "argmax_i w_i changed",
        "values": {"prev": pd, "now": cd, "w_prev": pw.get(pd), "w_now": cw.get(cd)},
        "computation": f"{pd} ({(pw.get(pd) or 0) * 100:.0f}%) -> {cd} ({(cw.get(cd) or 0) * 100:.0f}%)",
        "triggered": pd is not None and cd is not None and pd != cd,
    })
    rules.append({
        "rule": "R4_CONFIDENCE", "formula": "confidence grade changed",
        "values": {"prev": prev.confidence, "now": cur.confidence},
        "computation": f"{prev.confidence} -> {cur.confidence}",
        "triggered": prev.confidence != cur.confidence,
    })
    shifts = {m: round(((cw.get(m) or 0.0) - (pw.get(m) or 0.0)) * 100.0, 1) for m in set(pw) | set(cw)}
    big = {m: s for m, s in shifts.items() if abs(s) >= WEIGHT_SHIFT_PTS}
    rules.append({
        "rule": "R5_WEIGHT_SHIFT", "formula": "max_i |w_i,now - w_i,prev| x 100 >= 15 pts",
        "values": {"shifts_pts": shifts, "threshold_pts": WEIGHT_SHIFT_PTS},
        "computation": ", ".join(f"{m} {s:+.1f}" for m, s in sorted(big.items(), key=lambda kv: -abs(kv[1]))) or "no shift >= 15 pts",
        "triggered": bool(big),
    })
    return rules


def record_snapshot(db, pkg: Dict[str, Any], source_mode: str) -> Optional[Notification]:
    """Store a snapshot if the inputs changed; return the Notification created (if any rule fired)."""
    if db is None or not pkg.get("fusion"):
        return None
    region, variable, lead = pkg["region_id"], pkg["variable"], int(pkg["lead_hours"])
    strategy = pkg.get("strategy")
    h = _input_hash(pkg, source_mode)
    now = datetime.now(timezone.utc)
    with _lock:
        prev = (db.query(ForecastSnapshot)
                .filter(ForecastSnapshot.region_id == region, ForecastSnapshot.variable == variable,
                        ForecastSnapshot.lead_hours == lead, ForecastSnapshot.source_mode == source_mode,
                        ForecastSnapshot.strategy == strategy)
                .order_by(ForecastSnapshot.created_at.desc()).first())
        if prev is not None and prev.input_hash == h:
            return None
        cur = ForecastSnapshot(
            run_id=pkg.get("run_id"), region_id=region, variable=variable, lead_hours=lead, source_mode=source_mode,
            strategy=strategy, input_hash=h, fused_value=pkg["fusion"].get("fused_value"),
            probability=pkg["uncertainty"].get("probability"), confidence=pkg["uncertainty"].get("confidence"),
            alert_level=(pkg.get("extreme_signal") or {}).get("alert_level"),
            weights_json=dict(pkg["trust_modeling"]["final_weights"]),
            forecasts_json=dict(pkg["inputs"]["raw_forecasts"]), sources_json=_sources(pkg, now.isoformat()),
            created_at=now)
        db.add(cur)
        db.flush()
        notif = None
        if prev is not None:
            rules = evaluate_rules(prev, cur, variable)
            fired = [r for r in rules if r["triggered"]]
            if fired:
                escalated = ALERT_RANK.get(cur.alert_level, 0) > ALERT_RANK.get(prev.alert_level, 0)
                severity = ("CRITICAL" if escalated and ALERT_RANK.get(cur.alert_level, 0) >= 2 else
                            "WARNING" if any(r["rule"] in ("R1_FUSED_JUMP", "R2_ALERT_LEVEL") for r in fired) else "INFO")
                unit = pkg.get("unit") or {"rainfall": "mm", "temperature": "°C", "wind_speed": "m/s"}.get(variable, "")
                label = "Synthetic demo" if source_mode == "DEMO" else ("Live public models" if source_mode == "LIVE_PUBLIC" else "Stored data")
                title = f"{region} {variable} +{lead}h: {prev.fused_value} → {cur.fused_value} {unit}"
                msg = f"[{label}] " + "; ".join(r["computation"] for r in fired)
                notif = Notification(
                    severity=severity, category="FORECAST_CHANGE", title=title[:200], message=msg[:1000],
                    region_id=region, variable=variable, lead_hours=lead, previous_snapshot_id=prev.id,
                    current_snapshot_id=cur.id, created_at=now,
                    math_json={"rules": rules, "source_mode": source_mode, "strategy": strategy,
                               "previous_at": prev.created_at.isoformat() if prev.created_at else None,
                               "current_at": now.isoformat()},
                    sources_json={"previous": prev.sources_json, "current": cur.sources_json}, read_by=[])
                db.add(notif)
        db.commit()
        return notif


def to_dict(n: Notification, user_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": n.id, "created_at": n.created_at.isoformat() if n.created_at else None, "severity": n.severity,
        "category": n.category, "title": n.title, "message": n.message, "region_id": n.region_id,
        "variable": n.variable, "lead_hours": n.lead_hours, "previous_snapshot_id": n.previous_snapshot_id,
        "current_snapshot_id": n.current_snapshot_id, "math": n.math_json, "sources": n.sources_json,
        "read": bool(user_id and user_id in (n.read_by or [])),
    }
