"""
Records the VARUNA judge demo (≈3 min, 1920x1080) with a visible mouse cursor, click ripples,
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

INTRO = card("""<div class="k">Smart India Hackathon 2026 · SIH26081</div>
<h1>Six weather models.<br><span>One trust decision.</span></h1>
<p>VARUNA is a hybrid AI–NWP forecast-blending system for India: it decides which model to trust —
where, when and by how much — and proves it against IMD observations.</p>
<div class="row"><div class="c">India-first data</div><div class="c">14-stage traceable pipeline</div>
<div class="c">Every number explains itself</div><div class="c">Verified skill · closed loop</div><div class="c">Audit-grade governance</div></div>""",
                  "Decision support · not an official warning service")

OUTRO = card("""<div class="k">What you just saw</div>
<h1>Adaptive. Explainable. <span>Verified.</span></h1>
<div class="row"><div class="c">① Real Indian data path: IMD gridded truth, NCMRWF feeds first</div>
<div class="c">② 14 stages you can open, time and audit</div><div class="c">③ Σ w·F lineage behind every number</div>
<div class="c">④ Self-healing when a feed drops</div><div class="c">⑤ Change alerts with the maths</div>
<div class="c">⑥ Verify → skill memory → next weights</div><div class="c">⑦ Tamper-evident audit, separation of duties</div></div>
<p style="margin-top:28px">Ready for NCUM-G / NCUM-R / NEPS feeds — plug in, verify, blend.</p>""",
                 "github / docs: README · DATA_SOURCES.md · AUDIT_NOTES.md")


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


def api_token(api, email, pw):
    data = urllib.parse.urlencode({"username": email, "password": pw}).encode()
    return json.loads(urllib.request.urlopen(f"{api}/auth/login", data).read())["access_token"]


def api_post(api, path, body, token):
    req = urllib.request.Request(f"{api}{path}", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5173")
    ap.add_argument("--api", default=None, help="API base (default <url>/api)")
    ap.add_argument("--region", default="IN_TELANGANA_DECCAN")
    ap.add_argument("--email", default="analyst@ncmrwf.gov.in")
    ap.add_argument("--password", default="varuna2026")
    ap.add_argument("--out", default="demo")
    ap.add_argument("--theme", default="light")
    ap.add_argument("--debug", action="store_true", help="fast run + screenshot at every caption (no video)")
    a = ap.parse_args()
    api = a.api or a.url.rstrip("/") + "/api"
    os.makedirs(a.out, exist_ok=True)

    # Reset shared demo state before recording
    try:
        api_post(api, "/demo/inject-failure", {"action": "reset_scenario"}, api_token(api, a.email, a.password))
    except Exception as exc:
        print("reset skipped:", exc)

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

        async def settle(s=1.2):
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(s)

        # ── 0 · Title ─────────────────────────────────────────────────────────────────────────────
        await page.set_content(INTRO)
        await d.mark("intro", "Title card")
        await d.wait(6)

        # ── 1 · Manual sign-in (visible cursor + typing) ─────────────────────────────────────────
        await page.goto(a.url + "/")
        await settle(0.8)
        await d.chap("LAYER 0 · SECURE ACCESS")
        await d.cap("Signing in manually — no public sign-up; accounts are created by an administrator",
                    "Role-based access: forecaster · operations · analyst · admin · auditor", "login")
        await d.click(page.get_by_role("button", name="Sign in").first)
        await settle(0.4)
        await d.type(page.locator('input[type="email"]'), a.email, delay=28)
        await d.type(page.locator('input[type="password"]'), a.password, delay=45)
        await d.wait(0.3)
        await d.click(page.locator('button[type="submit"]'))
        await page.wait_for_url("**/dashboard**")
        await settle(0.8)

        # ── 2 · The problem ──────────────────────────────────────────────────────────────────────
        await page.goto(f"{a.url}/dashboard/control-room")
        await settle(1.2)
        sm = await page.evaluate("async (r) => (await fetch('/api/dashboard/summary?region_id='+r+'&lead_hours=48&source=auto')).json()", a.region)
        synthetic = sm.get("source_mode") == "SYNTHETIC_DEMO"
        await d.wm("Recorded with the labelled SYNTHETIC demo scenario — real IMD/NCMRWF runs use the same screens" if synthetic
                   else f"Live data · {sm.get('source_mode')} · issued {sm.get('issue_time') or ''}")
        vals = [v for v in (sm.get("model_forecasts") or {}).values() if v is not None]
        lo, hi = (min(vals), max(vals)) if vals else (0, 0)
        await d.chap("LAYER 1 · THE PROBLEM")
        spread = page.locator("text=model spread").locator("xpath=../..")
        await d.move_to(spread)
        await d.hl(spread)
        await d.cap(f"{len(vals)} models disagree for {sm.get('region_id', a.region).replace('IN_', '').replace('_', ' ').title()}: "
                    f"{lo:g} to {hi:g} mm of rain in 48 h. Which one should a forecaster trust?",
                    "VARUNA answers: trust each model by its verified skill — for this region, lead time and weather regime", "problem")
        await d.wait(5.5)
        src_badge = page.locator("text=/SYNTHETIC DEMO SCENARIO|NCMRWF\\/IMD|GLOBAL PUBLIC MODELS/i >> visible=true").first
        if await src_badge.count():
            await d.move_to(src_badge)
            await d.hl(src_badge)
            await d.cap("Every screen says honestly where its numbers come from",
                        "Synthetic demo · global models · NCMRWF/IMD feeds — never mixed up", "honesty")
            await d.wait(3.5)
        await d.hl(None)

        # ── 3 · India-first data ─────────────────────────────────────────────────────────────────
        await page.goto(f"{a.url}/dashboard/live-data")
        await settle(1.0)
        await d.chap("LAYER 2 · INDIA-FIRST DATA")
        tier = page.locator("text=1 · Indian sources (primary)")
        cards = tier.locator("xpath=following-sibling::div[1]")
        await d.move_to(cards, dy=0.3)
        await d.hl(cards)
        await d.cap("India first: IMD gridded rainfall is the ground truth, NCMRWF / IMD forecast files take priority",
                    "IMD Pune 0.25° grid · NCMRWF NCUM / NEPS drop folder · IMD API · IMDAA · ISRO MOSDAC", "india")
        await d.wait(5)
        table = page.locator("text=All Indian sources").locator("xpath=..")
        await page.mouse.wheel(0, 520)
        await d.wait(0.8)
        await d.hl(table)
        await d.cap("Each source shows its real status — available, configured, or awaiting institutional access",
                    "Global models (GFS · ECMWF IFS & AIFS · UK Met Office · DWD ICON) only fill gaps, never relabelled as Indian output", "sources")
        await d.wait(4.5)
        await d.hl(None)

        # ── 4 · Core pipeline ────────────────────────────────────────────────────────────────────
        await page.goto(f"{a.url}/dashboard/control-room")
        await settle(1.0)
        await d.chap("LAYER 3 · CORE 14-STAGE PIPELINE")
        trace = page.locator("text=Pipeline stage trace").locator("xpath=../..")
        await d.move_to(trace, dy=0.2)
        await d.hl(trace)
        await d.cap("The core: 14 stages run on every request — timed, inspectable, auditable",
                    "Ingest → QC → harmonise → context → skill → disagreement → trust → fusion → uncertainty → extremes → XAI → package → verify", "pipeline")
        await d.wait(4.5)
        for label, cap_t, cap_s, secs in [
            ("2. QC", "Quality control: every value is ACCEPTED, WARNING, REJECTED or QUARANTINED",
             "A physically impossible value is rejected; a stale feed is quarantined — never blended", 5.5),
            ("5. SKILL", "Historical skill: each model's verified error for this region and lead time",
             "Evidence is labelled — verified history vs prior — so nobody mistakes a guess for proof", 5.5),
            ("7. TRUST", "Adaptive trust: weights from skill, recent error and regime — always summing to 1",
             "Three strategies: ML meta-model · adaptive reliability · bias-corrected stacking", 6),
            ("9. FUSION", "Fusion: the blended forecast, with simple average and static blend kept as baselines",
             "So the gain over naive blending is always visible", 5),
        ]:
            await d.hl(None)
            await d.click(page.get_by_role("button", name=label).first)
            await d.wait(0.4)
            drawer = page.locator("aside").filter(has_text="of 14").first
            await d.hl(drawer)
            await d.cap(cap_t, cap_s, f"stage {label}")
            await d.wait(secs)
            await d.hl(None)
            await d.click(page.get_by_role("button", name="Close").first)
            await d.wait(0.3)

        # ── 5 · Explainability ───────────────────────────────────────────────────────────────────
        await d.chap("LAYER 4 · EVERY NUMBER EXPLAINS ITSELF")
        await page.mouse.wheel(0, 420)
        await d.wait(0.8)
        fused_card = page.locator("text=VARUNA fused forecast").locator("xpath=../../..")
        fused_num = fused_card.get_by_role("button", name="Show how this number was computed").nth(1)
        await d.click(fused_num)
        await d.wait(0.7)
        await d.cap("No black box: click any number to see its formula, every term, and where each input came from",
                    "Fused = Σ wᵢ·Fᵢ — weight × forecast for each model, with source, issue and received time", "lineage")
        await d.wait(8)
        await page.keyboard.press("Escape")
        await d.wait(0.4)
        weights_card = page.locator("text=Model trust weights").locator("xpath=../..")
        await d.move_to(weights_card, dy=0.25)
        wbtn = weights_card.get_by_role("button", name="Show how this number was computed").first
        await d.move_to(wbtn)
        await d.cap("Hover a weight: MAE, recent error, their evidence and the exact weighting formula",
                    "A forecaster can defend every weight in a briefing", "weights")
        await d.wait(5)

        # ── 6 · Resilience ───────────────────────────────────────────────────────────────────────
        await d.chap("LAYER 5 · RESILIENCE")
        drop = page.get_by_role("button", name=re.compile(r"^drop ")).first
        await d.move_to(drop)
        await d.hl(weights_card)
        await d.cap("What if the most trusted model's feed fails right now?", "", "dropout")
        await d.wait(2)
        await d.click(drop)
        await d.wait(1.8)
        await d.cap("All 14 stages re-run instantly: the failed model gets weight 0, the rest re-normalise, confidence drops honestly",
                    "Simulation only — nothing stored, no false alert", "dropout-result")
        await d.wait(5)
        reset = page.get_by_role("button", name=re.compile(r"^reset$")).first
        if await reset.count():
            await d.click(reset)
        await d.hl(None)
        await d.wait(0.8)

        # ── 7 · Change alerts ────────────────────────────────────────────────────────────────────
        await d.chap("LAYER 6 · SUDDEN-CHANGE ALERTS")
        await page.mouse.wheel(0, -2000)
        await d.wait(0.6)
        await d.cap("A new run arrives: the most trusted model suddenly jumps +60 mm…",
                    "(demo: the jump is injected as a simulation — and logged in the audit trail as one)" if synthetic else "", "change")
        token = await page.evaluate("() => localStorage.getItem('varuna_access_token')")
        top_model = max(sm.get("weights") or [{"model_id": "GFS", "weight": 0}], key=lambda w: w["weight"])["model_id"]
        if synthetic:
            api_post(api, "/demo/inject-failure", {"action": "simulate_model_bias", "model_id": top_model, "bias_magnitude": 60}, token)
        await d.wait(1)
        await d.click(page.get_by_role("button", name="Re-run").first)
        await d.wait(2.2)
        bell = page.get_by_role("button", name="Notifications", exact=False).first
        await d.move_to(bell)
        await d.hl(bell)
        await d.wait(0.8)
        await d.click(bell)
        await d.wait(1)
        item = page.locator("div.absolute button.w-full").first
        if await item.count():
            await d.click(item)
            await d.wait(1)
            await d.hl(None)
            await d.cap("VARUNA does not blindly follow the jump: the outlier loses trust, and the forecaster is alerted — with the maths",
                        "Which rules fired (IMD colour · dominant model · confidence · weight shift), their thresholds, both input sets and timestamps", "alert")
            await d.wait(7.5)
            await page.keyboard.press("Escape")
            await page.mouse.click(30, 30)
            close = page.get_by_role("button", name="Close").first
            if await close.count():
                await d.click(close)
        await d.hl(None)
        if synthetic:
            api_post(api, "/demo/inject-failure", {"action": "reset_scenario"}, token)
        await d.click(page.get_by_role("button", name="Re-run").first)
        await d.wait(0.8)

        # ── 8 · Closed loop ──────────────────────────────────────────────────────────────────────
        await d.chap("LAYER 7 · VERIFY → LEARN")
        await d.cap("")
        await d.click(page.get_by_role("button", name="14. VERIFY").first)
        await d.wait(0.8)
        drawer = page.locator("aside").filter(has_text="of 14").first
        await d.cap("When the observation arrives: verify against a rain gauge or the IMD gridded value",
                    "(demo entry shown; IMD gridded values are fetched automatically about 2 days later)", "verify")
        obs = drawer.locator("input").first
        await d.type(obs, "71.5", delay=80)
        await d.type(drawer.locator("input").nth(1), "Demo gauge entry", delay=25)
        await d.click(drawer.get_by_role("button", name="Verify", exact=True))
        await d.wait(1.2)
        await d.hl(drawer)
        await d.cap("Every model's error — and VARUNA's — is stored as verification evidence",
                    "", "verify-result")
        await d.wait(4)
        upd = drawer.get_by_role("button", name="Update skill memory")
        if await upd.count():
            await d.click(upd)
            await d.wait(1.2)
            await d.cap("Skill memory updated: the next forecast's weights learn from this error — a closed loop",
                        "Analysts update skill; admins approve strategy changes; nobody approves their own", "skill")
            await d.wait(5)
        await d.hl(None)
        await d.click(page.get_by_role("button", name="Close").first)

        # ── 9 · Governance / audit ───────────────────────────────────────────────────────────────
        await d.chap("LAYER 8 · TRUST & ACCOUNTABILITY")
        await page.goto(f"{a.url}/dashboard/verification")
        await settle(0.6)
        # switch to the auditor workspace (separate read-only role)
        await d.click(page.get_by_role("button", name="Model analyst").first if await page.get_by_role("button", name="Model analyst").count()
                      else page.locator("header button[aria-haspopup='menu']"))
        await d.wait(0.5)
        await d.click(page.get_by_role("menuitem", name="Sign out"))
        await settle(0.5)
        await d.click(page.get_by_role("button", name="Sign in").first)
        await settle(0.3)
        await d.type(page.locator('input[type="email"]'), "auditor@ncmrwf.gov.in", delay=22)
        await d.type(page.locator('input[type="password"]'), a.password, delay=35)
        await d.click(page.locator('button[type="submit"]'))
        await page.wait_for_url("**/dashboard**")
        await settle(1.0)
        await d.cap("A read-only auditor sees every sign-in, data fetch, verification and approval",
                    "Append-only, hash-chained log — even administrators cannot edit it", "audit")
        await d.wait(3.5)
        vbtn = page.get_by_role("button", name="Verify integrity")
        await d.click(vbtn)
        await d.wait(1.2)
        intact = page.locator("text=/Chain intact/").first
        if await intact.count():
            await d.hl(intact.locator("xpath=../.."))
        await d.cap("One click proves nothing was altered: every entry is SHA-256 chained to the previous one", "", "chain")
        await d.wait(5)
        await d.hl(None)
        await d.cap("")
        await d.chap("")

        # ── 10 · Outro ───────────────────────────────────────────────────────────────────────────
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
