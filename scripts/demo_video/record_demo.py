"""
Records the VARUNA judge demo (≈3 min, 1920x1080), structured around the five SIH26081 expected outcomes, with a visible mouse cursor, click ripples,
layer chapter tags, burned-in captions and highlight rings — driven through the real UI.

Usage (backend on :8000, frontend on :5173 or any URL serving the built app with /api proxied):
    python scripts/demo_video/record_demo.py --url http://127.0.0.1:5173 --out demo
    -> demo/varuna_demo.webm  (+ demo/timeline.json with scene start times for voice-over)
    ffmpeg -i demo/varuna_demo.webm -c:v libx264 -crf 18 -pix_fmt yuv420p demo/varuna_demo.mp4

Run it on YOUR machine after `python scripts/verify_real_data.py` has passed and the badge reads
NCMRWF/IMD + GLOBAL MODELS — the same script then shows real Indian data. With no real data stored
it records the clearly labelled synthetic demo scenario (watermark stays on).
"""
import argparse
import asyncio
import json
import re
import os
import time
import urllib.parse
import urllib.request

from playwright.async_api import async_playwright

OVERLAY_JS = r"""
(() => {
  if (window.__varunaOverlay) return; window.__varunaOverlay = true;
  const css = `
  #__cur{position:fixed;left:0;top:0;width:28px;height:28px;z-index:2147483647;pointer-events:none;transform:translate(-3px,-2px);transition:transform .02s}
  #__cur svg{filter:drop-shadow(0 2px 3px rgba(0,0,0,.45))}
  .__rip{position:fixed;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;border:3px solid #22d3ee;z-index:2147483646;pointer-events:none;animation:__rip .6s ease-out forwards}
  @keyframes __rip{from{transform:scale(.3);opacity:1}to{transform:scale(1.6);opacity:0}}
  #__cap{position:fixed;left:50%;bottom:34px;transform:translateX(-50%);max-width:78%;z-index:2147483645;pointer-events:none;
    background:rgba(8,15,30,.92);color:#f8fafc;border:1px solid rgba(34,211,238,.55);border-radius:14px;padding:14px 22px;
    font:600 21px/1.4 Inter,system-ui,sans-serif;box-shadow:0 12px 40px rgba(0,0,0,.45);text-align:center;opacity:0;transition:opacity .35s}
  #__cap small{display:block;font:500 15px/1.4 Inter,system-ui,sans-serif;color:#a5f3fc;margin-top:4px}
  #__chap{position:fixed;left:22px;top:72px;z-index:2147483645;pointer-events:none;background:#0e7490;color:#fff;
    font:700 13px/1 Inter,system-ui,sans-serif;letter-spacing:.08em;padding:9px 12px;border-radius:999px;opacity:0;transition:opacity .35s;box-shadow:0 6px 18px rgba(0,0,0,.3)}
  #__wm{position:fixed;right:16px;bottom:8px;z-index:2147483645;pointer-events:none;font:600 11px/1 Inter,system-ui,sans-serif;color:rgba(100,116,139,.95)}
  #__hl{position:fixed;z-index:2147483644;pointer-events:none;border:3px solid #f59e0b;border-radius:12px;box-shadow:0 0 0 9999px rgba(2,6,23,.35),0 0 24px rgba(245,158,11,.7);opacity:0;transition:all .45s ease}
  `;
  const st = document.createElement('style'); st.textContent = css;
  const add = () => {
    if (!document.body) return setTimeout(add, 30);
    document.head.appendChild(st);
    const cur = document.createElement('div'); cur.id = '__cur';
    cur.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24"><path d="M3 2l7.5 19 2.6-7.6L21 10.8z" fill="#fff" stroke="#0f172a" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    const cap = document.createElement('div'); cap.id = '__cap';
    const chap = document.createElement('div'); chap.id = '__chap';
    const wm = document.createElement('div'); wm.id = '__wm';
    const hl = document.createElement('div'); hl.id = '__hl';
    document.body.append(hl, cap, chap, wm, cur);
    const pos = window.__lastPos || {x: innerWidth / 2, y: innerHeight / 2};
    cur.style.left = pos.x + 'px'; cur.style.top = pos.y + 'px';
  };
  add();
  addEventListener('mousemove', e => { window.__lastPos = {x: e.clientX, y: e.clientY};
    const c = document.getElementById('__cur'); if (c) { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; } }, true);
  addEventListener('mousedown', e => { const r = document.createElement('div'); r.className = '__rip';
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; document.body.appendChild(r); setTimeout(() => r.remove(), 700); }, true);
  window.__cap = (t, s) => { const c = document.getElementById('__cap'); if (!c) return;
    if (!t) { c.style.opacity = 0; return; } c.innerHTML = t + (s ? '<small>' + s + '</small>' : ''); c.style.opacity = 1; };
  window.__chap = t => { const c = document.getElementById('__chap'); if (!c) return; c.textContent = t || ''; c.style.opacity = t ? 1 : 0; };
  window.__wm = t => { const c = document.getElementById('__wm'); if (c) c.textContent = t || ''; };
  window.__hl = r => { const h = document.getElementById('__hl'); if (!h) return; if (!r) { h.style.opacity = 0; return; }
    const p = 8; h.style.left = (r.x - p) + 'px'; h.style.top = (r.y - p) + 'px'; h.style.width = (r.width + 2 * p) + 'px';
    h.style.height = (r.height + 2 * p) + 'px'; h.style.opacity = 1; };
})();
"""

CARD = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(1200px 600px at 30% 20%,#0e7490 0%,#071226 55%,#030712 100%);
font-family:Inter,system-ui,sans-serif;color:#e2e8f0;overflow:hidden}
.w{max-width:1100px;padding:0 60px}.k{font:700 15px/1 Inter;letter-spacing:.22em;color:#67e8f9;text-transform:uppercase}
h1{font:800 64px/1.05 Inter;margin:18px 0 18px;color:#fff}h1 span{background:linear-gradient(90deg,#22d3ee,#a78bfa);-webkit-background-clip:text;color:transparent}
p{font:500 24px/1.5 Inter;color:#cbd5e1;margin:0 0 10px}.row{display:flex;gap:14px;flex-wrap:wrap;margin-top:26px}
.c{border:1px solid rgba(103,232,249,.35);background:rgba(15,23,42,.6);border-radius:12px;padding:12px 16px;font:600 17px/1.3 Inter;color:#e0f2fe}
.f{position:fixed;bottom:26px;left:60px;right:60px;display:flex;justify-content:space-between;font:500 14px/1 Inter;color:#64748b}
.fade{animation:f .9s ease both}@keyframes f{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
</style></head><body><div class="w fade">@@BODY@@</div><div class="f"><span>VARUNA · SIH26081 · MoES / NCMRWF</span><span>@@FOOT@@</span></div></body></html>"""


def card(body, foot):
    return CARD.replace("@@BODY@@", body).replace("@@FOOT@@", foot)

INTRO = card("""<div class="k">Smart India Hackathon 2026 · SIH26081 · MoES / NCMRWF</div>
<h1>Hybrid AI–NWP forecast blending.<br><span>Five outcomes, shown working.</span></h1>
<p>The problem statement asks for five things. This video shows each one in the running system, in order:</p>
<div class="row"><div class="c">① Dynamically blended forecast</div><div class="c">② Model weight maps</div>
<div class="c">③ Improved forecast skill</div><div class="c">④ Extreme-weather guidance</div><div class="c">⑤ Operational workflow</div></div>""",
             "Decision support · not an official warning service")

OUTRO = card("""<div class="k">SIH26081 expected outcomes</div>
<h1>All five, <span>working end to end.</span></h1>
<div class="row"><div class="c">① Blend re-weighted per region, lead time and regime</div>
<div class="c">② India weight map: dominant model per subdivision</div>
<div class="c">③ Lower error than the simple average and every single model</div>
<div class="c">④ IMD-category guidance, with the models behind it</div>
<div class="c">⑤ IMD/NCMRWF ingest → 14 stages → alert → verify → learn → audit</div></div>
<p style="margin-top:28px">Ready for NCUM-G / NCUM-R / NEPS feeds: plug in, verify, blend.</p>""",
             "README · DATA_SOURCES.md · scripts/verify_real_data.py")


class Director:
    def __init__(self, page, t0, speed=1.0, shots=None):
        self.page, self.t0, self.timeline, self.speed, self.shots = page, t0, [], speed, shots

    async def wait(self, s):
        await asyncio.sleep(s * self.speed)

    async def mark(self, scene, caption, sub=""):
        self.timeline.append({"t": round(time.time() - self.t0, 1), "scene": scene, "caption": caption, "sub": sub})

    async def cap(self, text, sub="", scene=None):
        await self.page.evaluate("([t,s]) => window.__cap && window.__cap(t,s)", [text, sub])
        await self.mark(scene or "", text, sub)
        if self.shots and text:
            await asyncio.sleep(0.5)
            await self.page.screenshot(path=os.path.join(self.shots, f"{len(self.timeline):02d}_{(scene or 'x').replace(' ', '_').replace('.', '')}.png"))

    async def chap(self, text):
        await self.page.evaluate("t => window.__chap && window.__chap(t)", text)

    async def wm(self, text):
        await self.page.evaluate("t => window.__wm && window.__wm(t)", text)

    async def hl(self, locator=None):
        if locator is None:
            await self.page.evaluate("() => window.__hl && window.__hl(null)")
            return
        try:
            box = await locator.bounding_box(timeout=4000)
        except Exception:
            box = None
        if box:
            await self.page.evaluate("r => window.__hl && window.__hl(r)", box)

    async def move_to(self, locator, steps=18, dx=0.5, dy=0.5):
        try:
            await locator.scroll_into_view_if_needed(timeout=4000)
            box = await locator.bounding_box(timeout=4000)
        except Exception as exc:
            print("move_to skipped:", str(exc).splitlines()[0][:120])
            return None
        if not box:
            return None
        x, y = box["x"] + box["width"] * dx, box["y"] + box["height"] * dy
        await self.page.mouse.move(x, y, steps=steps)
        return x, y

    async def click(self, locator, pause=0.25):
        pt = await self.move_to(locator)
        await asyncio.sleep(pause)
        if pt:
            await self.page.mouse.click(*pt)
        else:
            await locator.click()

    async def type(self, locator, text, delay=70):
        await self.click(locator)
        await locator.fill("")
        await locator.type(text, delay=delay)

    async def ripple_at(self, x, y):
        await self.page.evaluate("""([x,y]) => { const r = document.createElement('div'); r.className='__rip';
            r.style.left=x+'px'; r.style.top=y+'px'; document.body.appendChild(r); setTimeout(()=>r.remove(),700); }""", [x, y])

    async def select(self, locator, value):
        """Move the visible cursor to a dropdown, 'click' it and pick a value (native pickers do not render on video)."""
        pt = await self.move_to(locator)
        if pt:
            await self.ripple_at(*pt)
        await asyncio.sleep(0.35)
        await locator.select_option(str(value))

    async def nav(self, name):
        await self.click(self.page.locator("aside").get_by_role("button", name=re.compile("^" + re.escape(name))).first)


def api_token(api, email, pw):
    data = urllib.parse.urlencode({"username": email, "password": pw}).encode()
    return json.loads(urllib.request.urlopen(f"{api}/auth/login", data).read())["access_token"]


def api_post(api, path, body, token):
    req = urllib.request.Request(f"{api}{path}", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())


def api_get(api, path, token=None):
    req = urllib.request.Request(f"{api}{path}", headers={"Authorization": f"Bearer {token}"} if token else {})
    return json.loads(urllib.request.urlopen(req).read())


def top_weights(sm, n=3):
    ws = sorted(sm.get("weights") or [], key=lambda w: -w["weight"])[:n]
    return ", ".join(f"{w['model_id'].replace('_', ' ')} {round(w['weight'] * 100)}%" for w in ws)


def region_name(rid):
    return rid.replace("IN_", "").replace("_", " ").title()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5173")
    ap.add_argument("--api", default=None, help="API base (default <url>/api)")
    ap.add_argument("--region", default="IN_TELANGANA_DECCAN")
    ap.add_argument("--region2", default="IN_WESTERN_GHATS_KERALA", help="second region for the 'dynamic' comparison")
    ap.add_argument("--email", default="analyst@ncmrwf.gov.in")
    ap.add_argument("--password", default="varuna2026")
    ap.add_argument("--out", default="demo")
    ap.add_argument("--theme", default="light")
    ap.add_argument("--debug", action="store_true", help="fast run + screenshot at every caption (no usable video)")
    a = ap.parse_args()
    api = a.api or a.url.rstrip("/") + "/api"
    os.makedirs(a.out, exist_ok=True)

    tok = api_token(api, a.email, a.password)
    try:
        api_post(api, "/demo/inject-failure", {"action": "reset_scenario"}, tok)
    except Exception as exc:
        print("reset skipped:", exc)

    q = "variable=rainfall&weather_regime=HEAVY_RAINFALL&source=auto"
    s1 = api_get(api, f"/dashboard/summary?region_id={a.region}&lead_hours=48&{q}")
    s2 = api_get(api, f"/dashboard/summary?region_id={a.region2}&lead_hours=48&{q}")
    synthetic = s1.get("source_mode") == "SYNTHETIC_DEMO"
    bench = api_get(api, "/verification/compare")
    mae = {m["method"]: m["mae"] for m in bench.get("methods", [])}
    singles = {k: v for k, v in mae.items() if k in ("NCUM", "GFS", "WRF", "AI_WEATHER", "ECMWF_IFS", "UKMO_UM", "ICON")}
    best_single = min(singles.items(), key=lambda kv: kv[1]) if singles else ("—", None)
    stack, avg = mae.get("BIAS_CORRECTED_STACKING"), mae.get("SIMPLE_AVERAGE")

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--force-device-scale-factor=1.3333"])
        ctx = await browser.new_context(viewport={"width": 1440, "height": 810}, device_scale_factor=1.3333,
                                        record_video_dir=a.out, record_video_size={"width": 1920, "height": 1080})
        await ctx.add_init_script(OVERLAY_JS)
        await ctx.add_init_script(f"try{{localStorage.setItem('varuna_theme','{a.theme}');localStorage.setItem('varuna_source','auto')}}catch(e){{}}")
        page = await ctx.new_page()
        shots = None
        if a.debug:
            shots = os.path.join(a.out, "shots")
            os.makedirs(shots, exist_ok=True)
        d = Director(page, time.time(), speed=0.15 if a.debug else 1.0, shots=shots)

        async def settle(s=1.0):
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(s * d.speed if a.debug else s)

        selects = page.locator("select")   # context bar: region, variable, lead, regime, data

        # ── Title ────────────────────────────────────────────────────────────────────────────────
        await page.set_content(INTRO)
        await d.mark("intro", "Title card")
        await d.wait(6)

        # ── Manual sign-in ───────────────────────────────────────────────────────────────────────
        await page.goto(a.url + "/")
        await settle(0.6)
        await d.cap("Signing in by hand. There is no public sign-up: an administrator creates every account, one fixed role each",
                    "", "login")
        await d.click(page.get_by_role("button", name="Sign in").first)
        await settle(0.3)
        await d.type(page.locator('input[type="email"]'), a.email, delay=26)
        await d.type(page.locator('input[type="password"]'), a.password, delay=40)
        await d.click(page.locator('button[type="submit"]'))
        await page.wait_for_url("**/dashboard**")
        await settle(0.6)
        await d.wm("Recorded on the labelled SYNTHETIC demo scenario: real IMD / NCMRWF data uses the same screens" if synthetic
                   else f"Live data · {s1.get('source_mode')}")

        # ── ① Dynamically blended forecast ───────────────────────────────────────────────────────
        await d.nav("Control Room")
        await settle(1.0)
        await selects.nth(3).select_option("HEAVY_RAINFALL")
        await d.chap("OUTCOME ① · DYNAMICALLY BLENDED FORECAST")
        fused = page.locator("text=VARUNA fused forecast").locator("xpath=../..")
        await d.move_to(fused, dy=0.3)
        await d.hl(fused)
        vals = [v for v in (s1.get("model_forecasts") or {}).values() if v is not None]
        await d.cap(f"{region_name(a.region)}, rain in 48 h: the models say {min(vals):g} to {max(vals):g} mm. "
                    f"VARUNA's blend: {s1['fused_value']} mm",
                    f"The simple average would say {s1['baselines']['simple_average']} mm. The blend is not an average: "
                    "each model is weighted by its verified skill", "blend")
        await d.wait(6.5)
        await page.mouse.wheel(0, 380)
        await d.wait(0.6)
        wcard = page.locator("text=Model trust weights").locator("xpath=../..")
        await d.hl(wcard)
        await d.cap(f"Weights here: {top_weights(s1)}", "Non-negative and always summing to 1", "weights")
        await d.wait(4.5)
        await page.mouse.wheel(0, -1000)
        await d.wait(0.4)
        await d.hl(None)
        await d.select(selects.nth(0), a.region2)
        await settle(1.4)
        await page.mouse.wheel(0, 380)
        await d.wait(0.5)
        await d.hl(wcard)
        lvl1 = (s1.get("extreme_guidance") or {}).get("alert_level")
        lvl2 = (s2.get("extreme_guidance") or {}).get("alert_level")
        await d.cap(f"Switch to {region_name(a.region2)}: new weights ({top_weights(s2)}), new blend {s2['fused_value']} mm, IMD level {lvl1} → {lvl2}",
                    "Weights are recomputed for every region, lead time and weather regime, on every request", "dynamic")
        await d.wait(6.5)
        await d.hl(None)
        await page.mouse.wheel(0, -1000)
        await d.select(selects.nth(0), a.region)
        await settle(0.8)

        # ── ② Model weight maps ──────────────────────────────────────────────────────────────────
        await d.chap("OUTCOME ② · MODEL WEIGHT MAPS")
        await d.nav("Model Trust Map")
        await settle(1.6)
        await d.cap("The weight map: which model India should trust, subdivision by subdivision",
                    "Colour = the dominant model in that subdivision; the panel on the right lists the full weights", "map")
        await d.wait(5.5)
        ti = page.get_by_role("button", name="Trust Intensity").first
        if await ti.count():
            await d.click(ti)
            await d.wait(1.0)
            await d.cap("Trust intensity: how strongly the top model dominates. Pale areas mean the models must be read together",
                        "", "map-intensity")
            await d.wait(4.5)
        dis = page.get_by_role("button", name="Disagreement Spread").first
        if await dis.count():
            await d.click(dis)
            await d.wait(1.0)
            await d.cap("Disagreement: where the models diverge most, and so where the forecast is least certain", "", "map-spread")
            await d.wait(4.0)

        # ── ③ Improved forecast skill ────────────────────────────────────────────────────────────
        await d.chap("OUTCOME ③ · IMPROVED FORECAST SKILL")
        await d.nav("Verification Centre")
        await settle(1.4)
        table = page.locator("table").first
        await d.move_to(table, dy=0.15)
        await d.hl(table)
        await d.cap(f"Measured on {bench.get('sample_size', '')} held-out days the system never trained on (strict time order, no future data)",
                    "Synthetic benchmark: it shows method behaviour, not operational skill. The real-data version runs on IMD gridded truth"
                    if synthetic or "SYNTH" in str(bench.get("data_provenance", "")).upper() else "", "skill")
        await d.wait(5.5)
        row_s = page.locator("tr", has_text="Bias-Corrected Stacking").first
        await d.move_to(row_s)
        await d.hl(row_s)
        await d.cap(f"VARUNA's stacked blend: mean error {stack} mm. Simple average: {avg} mm. Best single model ({best_single[0]}): {best_single[1]} mm",
                    "Lower error than the simple average and than every individual model", "skill-row")
        await d.wait(7)
        await d.hl(None)
        loop = page.locator("text=Closed loop: verify → skill memory → next weights").first
        if await loop.count():
            await d.move_to(loop)
            await d.cap("And it keeps improving: every verified day feeds skill memory, which sets the next weights",
                        "Real-data skill comes from backfill against IMD gridded observations (Data sources → Run backfill)", "loop")
            await d.wait(4.5)

        # ── ④ Extreme-weather guidance ───────────────────────────────────────────────────────────
        await d.chap("OUTCOME ④ · EXTREME-WEATHER GUIDANCE")
        await d.nav("Extreme Events")
        await settle(2.2)
        matrix = page.locator("table").first
        await d.hl(matrix)
        await d.cap("Every subdivision and hazard, run through the pipeline and graded against IMD categories",
                    "Rain: heavy ≥ 64.5 mm (yellow), very heavy ≥ 115.6 (orange), extremely heavy ≥ 204.5 (red) · heatwave ≥ 40 °C · gale ≥ 14 m/s", "extremes")
        await d.wait(6)
        await d.hl(None)
        cell = page.get_by_role("button", name=re.compile(r"Heavy rainfall$")).first
        await d.click(cell)
        await d.wait(0.8)
        dossier = page.locator("text=Guidance dossier").locator("xpath=../../..")
        await d.hl(dossier)
        await d.cap("Click a cell: how far above the threshold, which models push it over, and how much trust they carry",
                    "So a forecaster can judge an orange signal, not just see it", "dossier")
        await d.wait(7)
        await d.hl(None)

        # ── ⑤ Operational workflow ───────────────────────────────────────────────────────────────
        await d.chap("OUTCOME ⑤ · OPERATIONAL WORKFLOW")
        await d.nav("Data Sources (India-first)")
        await settle(1.2)
        tier = page.locator("text=1 · Indian sources (primary)")
        cards = tier.locator("xpath=following-sibling::div[1]")
        await d.hl(cards)
        await d.cap("Step 1, data in: IMD gridded observations are the truth; NCMRWF / IMD forecast files take priority",
                    "Global models (GFS, ECMWF, UK Met Office, DWD) only fill gaps, and are always labelled as such", "data")
        await d.wait(5.5)
        await d.hl(None)

        await d.nav("Control Room")
        await settle(1.0)
        trace = page.locator("text=Pipeline stage trace").locator("xpath=../..")
        await d.hl(trace)
        await d.cap("Step 2, the 14-stage pipeline runs on every request; each stage shows its result and time",
                    "Ingest → QC → harmonise → context → skill → disagreement → trust → fusion → uncertainty → extremes → explanation → package → verify", "pipeline")
        await d.wait(5)
        await d.hl(None)
        await d.click(page.get_by_role("button", name="2. QC").first)
        await d.wait(0.6)
        drawer = page.locator("aside").filter(has_text="of 14").first
        await d.hl(drawer)
        await d.cap("Click any stage to open it. Quality control: impossible values are rejected and stale feeds quarantined, never blended",
                    "", "qc")
        await d.wait(5)
        await d.hl(None)
        await d.click(page.get_by_role("button", name="Close").first)
        await d.wait(0.3)

        await page.mouse.wheel(0, 380)
        await d.wait(0.5)
        drop = page.get_by_role("button", name=re.compile(r"^drop ")).first
        await d.hl(wcard)
        await d.cap("Step 3, a feed fails: drop the most trusted model", "", "dropout")
        await d.wait(1.6)
        await d.click(drop)
        await d.wait(1.6)
        await d.cap("All 14 stages re-run at once: the failed model gets weight 0, the others re-normalise, and confidence drops honestly",
                    "Simulation only: nothing stored", "dropout-result")
        await d.wait(5)
        reset = page.get_by_role("button", name=re.compile(r"^reset$")).first
        if await reset.count():
            await d.click(reset)
        await d.hl(None)
        await page.mouse.wheel(0, -2000)
        await d.wait(0.4)

        token = await page.evaluate("() => localStorage.getItem('varuna_access_token')")
        top_model = max(s1.get("weights") or [{"model_id": "GFS", "weight": 0}], key=lambda w: w["weight"])["model_id"]
        await d.cap(f"Step 4, a new run arrives: {top_model.replace('_', ' ')} suddenly jumps by +60 mm",
                    "(demo: the jump is injected as a simulation and logged in the audit trail as one)" if synthetic else "", "change")
        if synthetic:
            api_post(api, "/demo/inject-failure", {"action": "simulate_model_bias", "model_id": top_model, "bias_magnitude": 60}, token)
        await d.wait(0.8)
        await d.click(page.get_by_role("button", name="Re-run").first)
        await d.wait(2.0)
        bell = page.get_by_role("button", name="Notifications", exact=False).first
        await d.hl(bell)
        await d.click(bell)
        await d.wait(0.8)
        item = page.locator("div.absolute button.w-full").first
        if await item.count():
            await d.click(item)
            await d.wait(1)
            await d.hl(None)
            await d.cap("The forecaster is alerted, with the rule that fired, its threshold, both input sets and the times",
                        "VARUNA cuts the trust of the model that jumped instead of following it", "alert")
            await d.wait(7)
            await page.keyboard.press("Escape")
            close = page.get_by_role("button", name="Close").first
            if await close.count():
                await d.click(close)
        await d.hl(None)
        if synthetic:
            api_post(api, "/demo/inject-failure", {"action": "reset_scenario"}, token)
        await d.click(page.get_by_role("button", name="Re-run").first)
        await d.wait(0.8)

        await d.click(page.get_by_role("button", name="14. VERIFY").first)
        await d.wait(0.7)
        drawer = page.locator("aside").filter(has_text="of 14").first
        await d.cap("Step 5, the observation arrives: verify against a rain gauge or the IMD gridded value",
                    "(demo gauge entry; IMD gridded values can be fetched about 2 days after the valid day)", "verify")
        await d.type(drawer.locator("input").first, "71.5", delay=70)
        await d.type(drawer.locator("input").nth(1), "Demo gauge entry", delay=22)
        await d.click(drawer.get_by_role("button", name="Verify", exact=True))
        await d.wait(1.0)
        await d.hl(drawer)
        upd = drawer.get_by_role("button", name="Update skill memory")
        await d.cap("Every model's error, and VARUNA's own, is stored as evidence", "", "verify-result")
        await d.wait(3.5)
        if await upd.count():
            await d.click(upd)
            await d.wait(1.0)
            await d.cap("Step 6, learn: skill memory is updated, so the next forecast's weights use this error",
                        "Analysts update skill; changes to the method need an administrator's approval", "skill")
            await d.wait(4.5)
        await d.hl(None)
        await d.click(page.get_by_role("button", name="Close").first)

        # Step 7: audit, as a separate read-only account
        await d.click(page.locator("header button[aria-haspopup='menu']"))
        await d.wait(0.6)
        menu = page.locator("[role=menu]").first
        await d.hl(menu)
        await d.cap("Step 7, accountability: each account has one fixed role. Auditing needs a separate auditor account",
                    "", "role")
        await d.wait(4)
        await d.hl(None)
        await d.click(page.get_by_role("menuitem", name="Sign out"))
        await settle(0.4)
        await d.click(page.get_by_role("button", name="Sign in").first)
        await settle(0.3)
        await d.type(page.locator('input[type="email"]'), "auditor@ncmrwf.gov.in", delay=20)
        await d.type(page.locator('input[type="password"]'), a.password, delay=32)
        await d.click(page.locator('button[type="submit"]'))
        await page.wait_for_url("**/dashboard**")
        await settle(1.0)
        await d.cap("The auditor sees every sign-in, fetch, verification and skill update, including the simulated jump",
                    "Append-only and hash-chained: even administrators cannot edit it", "audit")
        await d.wait(4)
        await d.click(page.get_by_role("button", name="Verify integrity"))
        await d.wait(1.2)
        intact = page.locator("text=/Chain intact/").first
        if await intact.count():
            await d.hl(intact.locator("xpath=../.."))
        await d.cap("One click proves nothing was altered: each entry is SHA-256 chained to the one before", "", "chain")
        await d.wait(5)
        await d.hl(None)
        await d.cap("")
        await d.chap("")

        # ── Outro ───────────────────────────────────────────────────────────────────────────────
        await page.set_content(OUTRO)
        await d.mark("outro", "Closing card")
        await d.wait(8)

        video_path = await page.video.path()
        await ctx.close()
        await browser.close()
        final = os.path.join(a.out, "varuna_demo.webm")
        os.replace(video_path, final)
        with open(os.path.join(a.out, "timeline.json"), "w") as f:
            json.dump({"duration_s": round(time.time() - d.t0, 1), "scenes": d.timeline}, f, indent=2)
        print("video:", final, "duration ~", round(time.time() - d.t0, 1), "s")


if __name__ == "__main__":
    asyncio.run(main())
