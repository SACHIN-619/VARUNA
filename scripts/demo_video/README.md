# VARUNA judge demo video (≈3 min)

`record_demo.py` drives the real UI in Chromium and records a 1920×1080 video. The recording includes:

- a visible mouse cursor with a ripple on every click
- a manual sign-in, typed on screen
- a "LAYER n" chapter tag for each part
- burned-in captions
- an amber highlight on the element being explained

`demo/VARUNA_demo_3min.mp4` was recorded from the **synthetic demo scenario**. The app's own badge says so, and a watermark stays on screen the whole time. For the submission, re-record on your machine after real data is in (see below): the same script then shows IMD / NCMRWF / global-model data.

## Layers in the video

| # | Layer | What the judge sees |
|---|---|---|
| 0 | Secure access | Typed sign-in, role-based accounts, no public sign-up |
| 1 | The problem | Models disagree (min–max spread) — "which one do you trust?"; honest data-source badge |
| 2 | India-first data | IMD gridded truth, NCMRWF drop folder, IMD API, IMDAA, MOSDAC with real statuses; global models only as gap-fillers |
| 3 | Core 14-stage pipeline | Click QC → Skill → Trust → Fusion: each stage's inputs, outputs, timing |
| 4 | Every number explains itself | Fused value popover: Σ w·F terms, sources, issue/received time; weight explanation |
| 5 | Resilience | Drop the most-trusted feed → all 14 stages re-run, weights re-normalise |
| 6 | Sudden-change alerts | +60 mm jump in one model → the outlier loses trust, the bell fires, and the alert shows the rule maths |
| 7 | Verify → learn | Stage 14: observation entered, per-model errors, skill memory updated (closed loop) |
| 8 | Trust & accountability | Auditor workspace, hash-chained audit log, "Verify integrity" |

## Re-recording with real data (recommended for submission)

```bash
# 1. backend + frontend running, real data loaded
python scripts/verify_real_data.py --days 60        # must end with 0 failed
# 2. record
pip install playwright && python -m playwright install chromium
python scripts/demo_video/record_demo.py --url http://localhost:3000 --api http://localhost:8000/api --out demo
# 3. encode (≈ 3:00; adjust 0.775 so the output is ~180 s — the webm runs ~18 % slower than wall time)
ffmpeg -ss 0.45 -i demo/varuna_demo.webm -vf "setpts=0.775*PTS,fps=30,fade=t=in:st=0:d=0.6" -c:v libx264 -crf 22 -pix_fmt yuv420p demo/VARUNA_demo.mp4
```

Options: `--region IN_TELANGANA_DECCAN`, `--theme dark`, `--debug` (fast dry run that saves a screenshot at every caption instead of a usable video).

Before recording:

- Run a backfill so the Skill stage shows verified history.
- Close other browser tabs.
- If you have no real NCMRWF files, leave that card at NOT CONFIGURED. Don't fake it.

## Voice-over script

Times are approximate (±5 s). Align them in your editor against the captions, and keep the narration short; the captions carry the detail.

| ~Time | Say |
|---|---|
| 0:00 | "Six weather models, one trust decision. This is VARUNA, built for MoES and NCMRWF." |
| 0:07 | "Access is role-based. There is no public sign-up; an administrator creates every account." |
| 0:18 | "For Telangana, the models disagree by more than fifty millimetres. Which one should the forecaster trust?" |
| 0:24 | "VARUNA always tells you where its numbers come from." |
| 0:30 | "India first. IMD gridded rainfall is our ground truth, and NCMRWF and IMD forecast files take priority. Global models only fill gaps." |
| 0:42 | "This is the core: fourteen stages on every request, each one open, timed and auditable." |
| 0:48 | "Quality control: impossible values are rejected and stale feeds quarantined, never blended." |
| 0:56 | "Skill: each model's verified error for this region and lead time, with the evidence labelled." |
| 1:04 | "Trust: weights from skill, recent error and the weather regime, always summing to one." |
| 1:12 | "Fusion, with the simple average kept beside it, so the gain is always visible." |
| 1:21 | "No black box. Every number opens its own formula, every term, and the source and time of each input." |
| 1:36 | "What if the most trusted feed fails? All fourteen stages re-run instantly, and confidence drops honestly." |
| 1:48 | "Now a new run jumps by sixty millimetres. VARUNA doesn't follow it blindly: the outlier loses trust, and the forecaster is alerted with the exact maths." |
| 2:09 | "When the observation arrives, every model's error and VARUNA's own are stored, and skill memory learns from them. That closes the loop." |
| 2:40 | "An auditor sees everything. One click proves nothing was altered." |
| 2:50 | "Adaptive, explainable, verified. VARUNA is ready for NCUM and NEPS feeds." |

Record the voice separately, for example with Audacity, then add it as an audio track. A soft background track at about −25 dB under the voice works well.
