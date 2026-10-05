# VARUNA judge demo video (3 min)

`record_demo.py` drives the real UI in Chromium and records a 1920×1080 video. The recording includes:

- a visible mouse cursor with a ripple on every click
- a manual sign-in, typed on screen
- an "OUTCOME n" tag for each part
- burned-in captions, with numbers read live from the API (nothing typed into the script)
- an amber highlight on the element being explained

The video follows the **five expected outcomes in the SIH26081 problem statement**, in order, and shows each one by clicking through full pages (no hover tooltips).

The rendered video is **not stored in the repository**. When no real data is loaded, it is recorded on the labelled synthetic demo scenario, and a watermark says so. For the submission, load real data first and record on your machine (see below).

## Structure

| Video time | Tag | What the judge sees |
|---|---|---|
| 0:00 | Title | The five SIH26081 expected outcomes |
| 0:05 | Sign-in | Typed manual sign-in; no public sign-up |
| 0:15 | ① Dynamically blended forecast | Model spread vs VARUNA's blend vs simple average. The region is switched and the weights, blend and IMD colour change |
| 0:37 | ② Model weight maps | India map: dominant model, trust intensity, disagreement |
| 0:55 | ③ Improved forecast skill | Held-out benchmark: stacked blend vs simple average vs every single model |
| 1:12 | ④ Extreme-weather guidance | Risk matrix for every subdivision × hazard against IMD categories; dossier with the models above and below the threshold |
| 1:26 | ⑤ Operational workflow | India-first data, then the 14 stages and QC, then a dropped feed, then a sudden jump and the alert with its maths, then verify, then the skill update, then the fixed role and the auditor's hash-chain check |
| 2:50 | Close | The five outcomes ticked off |

## Recording with real data (recommended for submission)

```bash
# 1. backend + frontend running, real data loaded
python scripts/verify_real_data.py --days 60        # must end with 0 failed
# 2. record (≈ 4 min of wall time)
pip install playwright && python -m playwright install chromium
python scripts/demo_video/record_demo.py --url http://localhost:3000 --api http://localhost:8000/api --out demo_out
# 3. encode to 3:00. The webm runs longer than wall time; F = 180 / (webm duration in s)
ffprobe -v error -show_entries format=duration -of csv=p=0 demo_out/varuna_demo.webm
ffmpeg -ss 0.45 -i demo_out/varuna_demo.webm -vf "setpts=F*PTS,fps=30,fade=t=in:st=0:d=0.6" -c:v libx264 -crf 22 -pix_fmt yuv420p VARUNA_demo.mp4
```

Keep `demo_out/` outside the repository, or delete it after encoding.

Options:

- `--region` / `--region2` choose the two regions compared in outcome ①.
- `--theme dark` records in dark mode.
- `--debug` is a fast dry run that saves a screenshot at every caption instead of a usable video.

Before recording:

- Run a backfill so skill shows verified history.
- If you have no real NCMRWF files, leave that card at NOT CONFIGURED. Don't fake it.
- If you record on real data, re-read the numbers in the voice-over below against your captions; the script uses the synthetic run's numbers.

## Voice-over (3:00, about 430 words)

Speak at a calm pace, roughly 150 words a minute. Times are video times, ±3 s; let the captions carry the exact numbers.

**0:00 — Title**
"Six forecast models. Six different answers. Every day, a forecaster at NCMRWF has to decide which one to believe. SIH26081 asks for a hybrid AI–NWP blending system with five outcomes. This is VARUNA, and you'll see all five, working."

**0:05 — Sign-in**
"No public sign-up. An administrator creates every account, and each account has one fixed role."

**0:15 — ① Dynamically blended forecast**
"Telangana, rain in forty-eight hours. The models range from forty-seven to a hundred and three millimetres. A simple average says seventy-four. VARUNA says sixty-seven point two, because it weights each model by its verified skill for this region, this lead time and this weather regime. Switch to the Western Ghats: new weights, a new blend, and the IMD level moves from yellow to orange. That is a dynamic blend, recomputed on every request."

**0:37 — ② Model weight maps**
"Outcome two: the weight map. For every Indian subdivision, which model deserves trust. How strongly it dominates. And where the models disagree, which is exactly where a forecaster should look twice."

**0:55 — ③ Improved forecast skill**
"Outcome three: does blending actually help? On a hundred and twenty-five held-out days, in strict time order, VARUNA's stacked blend has a lower error than the simple average and lower than every single model. This benchmark is synthetic and labelled as such. The same test runs against IMD gridded observations once real data is loaded."

**1:12 — ④ Extreme-weather guidance**
"Outcome four: extreme weather. Every subdivision and hazard, graded against IMD categories. Click a cell and you see how far above the threshold it is, which models push it over, and how much trust they carry. That turns an orange signal into a decision a forecaster can defend."

**1:26 — ⑤ Operational workflow**
"Outcome five: the operational workflow. India first. IMD gridded observations are the truth, and NCMRWF and IMD forecast files take priority. Global models only fill gaps."
"Fourteen stages run on every request, and each can be opened. Quality control rejects impossible values and quarantines stale feeds."
"Now the most trusted feed fails. All fourteen stages re-run at once; the weights re-normalise, and confidence drops honestly."
"A new run jumps by sixty millimetres. VARUNA doesn't follow it blindly. It cuts that model's trust and alerts the forecaster, showing the rule, the threshold and both sets of inputs with their times."
"When the observation arrives, every model's error is stored, and skill memory learns from it. Tomorrow's weights are better than today's."
"And it's accountable. An auditor, on a separate account, sees every action, including our simulated jump. One click proves the log is untouched."

**2:50 — Close**
"Dynamic blending. Weight maps. Measured skill. Extreme-weather guidance. A complete operational loop. VARUNA is ready for NCUM and NEPS feeds: plug them in, verify, blend."

Record the voice separately (for example in Audacity) and add it as an audio track. A soft background track at about −25 dB under the voice works well.

If you record on real data, replace the numbers spoken in ① and ③ with the ones in your captions. Never say "IMD" or "NCMRWF" data for a synthetic recording.
