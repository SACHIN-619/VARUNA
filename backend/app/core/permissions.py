"""
VARUNA role -> permission matrix (single source of truth for API and UI).

Separation of duties:
  * ADMIN manages identity, configuration and approves changes, but cannot alter
    forecast values, verification history or audit records.
  * ANALYST runs science (experiments, skill updates) and *proposes* model changes;
    a different ADMIN must approve them.
  * OPERATIONS runs data acquisition (ingest, live fetch) and pipeline operations.
  * FORECASTER consumes forecast intelligence and can verify a run with an observation.
  * AUDITOR is read-only across forecasts, provenance and the audit trail.
"""
from typing import Dict, List, Set

ROLES = ["FORECASTER", "OPERATIONS", "ANALYST", "ADMIN", "AUDITOR"]

PERMISSIONS: Dict[str, str] = {
    "forecast:view": "View forecast intelligence, trust, maps and explanations",
    "notifications:view": "Receive forecast-change notifications",
    "verification:view": "View verification and benchmark results",
    "verification:run": "Verify a forecast run against an observation",
    "data:ingest": "Upload datasets",
    "live:fetch": "Fetch live public forecasts / observations and backfill verification",
    "pipeline:operate": "Inspect sources, jobs and pipeline health",
    "skill:update": "Recompute model skill memory from verification history",
    "experiment:run": "Run benchmark experiments",
    "change:propose": "Propose model / configuration changes",
    "change:approve": "Approve or reject proposed changes (never one's own)",
    "users:manage": "Create users, change roles, deactivate accounts",
    "config:view": "View system configuration",
    "audit:view": "View and integrity-check the audit trail",
    "demo:inject": "Use the failure-injection demo controls",
}

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "FORECASTER": {"forecast:view", "notifications:view", "verification:view", "verification:run", "demo:inject"},
    "OPERATIONS": {"forecast:view", "notifications:view", "verification:view", "verification:run",
                   "data:ingest", "live:fetch", "pipeline:operate", "demo:inject"},
    "ANALYST": {"forecast:view", "notifications:view", "verification:view", "verification:run",
                "data:ingest", "skill:update", "experiment:run", "change:propose", "pipeline:operate", "demo:inject"},
    "ADMIN": {"forecast:view", "notifications:view", "verification:view", "pipeline:operate",
              "change:approve", "users:manage", "config:view", "audit:view", "live:fetch", "data:ingest", "demo:inject"},
    "AUDITOR": {"forecast:view", "verification:view", "audit:view", "config:view", "pipeline:operate"},
}


def normalize_role(role: str) -> str:
    r = (role or "").upper()
    return "ANALYST" if r == "MODEL_ANALYST" else r


def permissions_for(role: str) -> List[str]:
    return sorted(ROLE_PERMISSIONS.get(normalize_role(role), set()))


def has_permission(role: str, perm: str) -> bool:
    return perm in ROLE_PERMISSIONS.get(normalize_role(role), set())


def region_allowed(scope, region_id: str) -> bool:
    if not scope or "*" in scope:
        return True
    return region_id in scope
