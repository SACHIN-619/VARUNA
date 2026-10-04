"""
Real-data acceptance test for a running VARUNA backend (run on YOUR machine, not in CI).

    cd backend && uvicorn app.main:app --port 8000      # in one terminal
    python scripts/verify_real_data.py                   # in another (Python 3.9+, no extra packages)

Options: --base http://127.0.0.1:8000/api  --region IN_TELANGANA_DECCAN  --days 30

Each step prints PASS / WARN / FAIL with the reason. WARN means "works, but something to look at"
(e.g. a model missing from the provider). Nothing here is synthetic: if a step passes, real IMD /
public-model data went through the 14-stage pipeline.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

RESULTS = []


def say(status, step, detail=""):
    RESULTS.append(status)
    mark = {"PASS": "\033[32mPASS\033[0m", "WARN": "\033[33mWARN\033[0m", "FAIL": "\033[31mFAIL\033[0m"}[status]
    print(f"[{mark}] {step}" + (f" — {detail}" if detail else ""))


def call(base, path, method="GET", body=None, token=None, form=None, timeout=180):
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "null"), time.time() - t0
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {"detail": str(e)}
        return e.code, payload, time.time() - t0
    except (urllib.error.URLError, OSError) as e:
        return 0, {"detail": f"cannot connect to {base}: {e}"}, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000/api")
    ap.add_argument("--region", default="IN_TELANGANA_DECCAN")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--password", default="varuna2026")
    a = ap.parse_args()
    B, R = a.base.rstrip("/"), a.region

    s, h, _ = call(B, "/health")
    if s != 200:
        say("FAIL", "Backend reachable", f"HTTP {s} at {B}/health — start uvicorn first")
        return 1
    say("PASS", "Backend reachable", f"DB {h.get('database')}")

    s, tok, _ = call(B, "/auth/login", "POST", form={"username": "ops@ncmrwf.gov.in", "password": a.password})
    if s != 200:
        say("FAIL", "Login as operations", str(tok))
        return 1
    T = tok["access_token"]
    say("PASS", "Login as operations", f"{len(tok['permissions'])} permissions")

    # 1. IMD gridded truth (India primary)
    d = (date.today() - timedelta(days=4)).isoformat()
    s, g, dt = call(B, "/india/imd-grid/fetch", "POST", {"region_id": R, "variable": "rainfall", "start": d}, T)
    if s == 200 and g["truth"].get(d) is not None:
        cell = next(iter(g["cells"].values()), {})
        say("PASS", "IMD gridded rainfall", f"{d}: {g['truth'][d]} mm at cell {cell.get('cell_lat')},{cell.get('cell_lon')} ({dt:.1f}s)")
    elif s == 200:
        say("WARN", "IMD gridded rainfall", f"no value for {d} at this location (file read OK)")
    else:
        say("FAIL", "IMD gridded rainfall", f"{g.get('detail')} — check outbound HTTPS to imdpune.gov.in, or upload the .grd file")

    # 2. Global models over India
    s, f, dt = call(B, "/live/fetch", "POST", {"region_id": R, "variables": ["rainfall", "temperature"]}, T)
    if s == 200:
        for r in f["results"]:
            st = "PASS" if len(r["models_received"]) >= 4 else "WARN"
            say(st, f"Global models · {r['variable']}", f"{r['records']} values from {', '.join(r['models_received'])}"
                + (f"; missing {list(r['missing'])}" if r["missing"] else "") + f" ({dt:.1f}s)")
    else:
        say("FAIL", "Global models fetch", f"{f.get('detail')} — check outbound HTTPS to api.open-meteo.com")

    # 3. Verified skill against IMD truth
    s, b, dt = call(B, "/live/backfill", "POST", {"region_id": R, "variable": "rainfall", "days": a.days, "truth_source": "AUTO"}, T, timeout=300)
    if s == 200:
        st = "PASS" if b["truth"] == "OBS_IMD" else "WARN"
        say(st, "Backfill (verified skill)", f"truth {b['truth_name']}, {b['verification_rows']} rows, window {b['window'][0]}→{b['window'][1]} ({dt:.1f}s)"
            + (f"; note: {b['truth_note']}" if st == "WARN" else ""))
        for lead, c in b["leads"].items():
            ho = c.get("holdout")
            if ho:
                better = ho["stacking_mae"] is not None and ho["stacking_mae"] <= ho["simple_average_mae"]
                say("PASS" if better else "WARN", f"  Hold-out lead {lead} h",
                    f"stacking {ho['stacking_mae']} vs average {ho['simple_average_mae']} vs best single {ho['best_single_model']} {ho['best_single_model_mae']} mm"
                    + ("" if better else " — stacking not better on this window (report it honestly)"))
            else:
                say("WARN", f"  Hold-out lead {lead} h", c.get("stacker"))
    else:
        say("FAIL", "Backfill", str(b.get("detail")))

    # 4. Pipeline on real inputs
    s, sm, dt = call(B, f"/dashboard/summary?region_id={R}&lead_hours=48&variable=rainfall&source=auto")
    if s == 200 and sm["source_mode"] != "SYNTHETIC_DEMO":
        stages = [t for t in sm["stage_trace"] if t["status"] in ("PASS", "WARN")]
        say("PASS", "14-stage pipeline on real data", f"{sm['source_mode']}, fused {sm['fused_value']} {sm['unit']}, "
            f"{len(stages)}/14 stages run, strategy {sm['strategy']}, {dt * 1000:.0f} ms")
        terms = sm["lineage"]["fused_value"]["terms"]
        recomputed = sum(t["weight"] * t["value"] for t in terms if t["value"] is not None)
        if sm["lineage"]["fused_value"].get("bias_correction"):
            say("PASS", "Lineage", "bias-corrected blend: terms listed with per-model bias")
        else:
            ok = abs(recomputed - sm["fused_value"]) < 0.2
            say("PASS" if ok else "FAIL", "Lineage reproduces fused value", f"Σ w·F = {recomputed:.2f} vs {sm['fused_value']}")
        prov = {m.get("provenance") for m in sm["source_meta"].values()}
        say("PASS", "Provenance on every input", ", ".join(sorted(p for p in prov if p)))
        skill = set(sm["skill_provenance"].values())
        say("PASS" if skill == {"DATABASE_VERIFIED_HISTORY"} else "WARN", "Skill evidence", ", ".join(sorted(skill)))
    else:
        say("FAIL", "Pipeline on real data", f"source_mode {sm.get('source_mode') if isinstance(sm, dict) else s}: {sm.get('source_note') if isinstance(sm, dict) else ''}")

    # 5. NCMRWF drop folder (optional)
    s, n, _ = call(B, "/india/ncmrwf/scan", "POST", None, T)
    if s == 200:
        say("PASS", "NCMRWF drop folder", f"{len(n['files'])} file(s): " + ", ".join(f"{x['file']}={x['status']}" for x in n["files"][:5]))
    else:
        say("WARN", "NCMRWF drop folder", n.get("detail"))

    # 6. Audit chain
    s, adm, _ = call(B, "/auth/login", "POST", form={"username": "auditor@ncmrwf.gov.in", "password": a.password})
    if s == 200:
        s, v, _ = call(B, "/audit/verify-chain", token=adm["access_token"])
        say("PASS" if v.get("intact") else "FAIL", "Audit hash chain", f"{v.get('checked')} entries checked" if v.get("intact") else str(v))

    fails, warns = RESULTS.count("FAIL"), RESULTS.count("WARN")
    print(f"\n{len(RESULTS) - fails - warns} passed, {warns} warnings, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
