# VARUNA Frontend — Forecast Intelligence Control Room

React 18 + TypeScript + Vite 6 + Tailwind CSS 3. Talks to the FastAPI backend under `/api`.

## Run

```bash
npm install
npm run dev          # http://localhost:3000, proxies /api → http://127.0.0.1:8000
npm run typecheck    # tsc --noEmit
npm run build        # type-check + production build in dist/
npm run preview
```

| Env var | Purpose |
|---|---|
| `VITE_API_BASE` | API base URL when the frontend and backend are deployed on different hosts (default `/api`) |
| `VITE_PROXY_TARGET` | Dev-server proxy target (default `http://127.0.0.1:8000`) |

## Deploy on Vercel

`vercel.json` is included. In Vercel: **Import project → Root Directory `frontend`** (framework Vite, build `npm run build`, output `dist`).

- `/api/*` is rewritten to the Render API (`https://varuna-a4ou.onrender.com/api/*`). The browser stays on the Vercel domain, so CORS doesn't apply. If your Render URL changes, edit the rewrite in `vercel.json`.
- Every other path falls back to `index.html`, so `/dashboard/...` links work on refresh.
- Leave `VITE_API_BASE` unset when using the rewrite. Set it only to call the API directly; then add the Vercel domain to `CORS_ORIGINS` on Render.
- Render's free tier sleeps after about 15 minutes idle, and the first request then waits for it to wake. Open the site a minute before anyone looks at it.

## Routes

| URL | Page |
|---|---|
| `/` | Landing page (always dark by design) |
| `/login` | Sign-in (demo accounts listed on the page, password `varuna2026`) |
| `/dashboard/<page>` | `<page>` ∈ `control-room`, `forecast`, `fusion`, `trust-map`, `regional`, `extremes`, `why-this-forecast`, `what-changed`, `verification`, `model-performance`, `failure-memory`, `operations`, `live-data`, `experiments`, `data-health`, `provenance`, `audit`, `governance`, `system-health`, `api-docs`, `settings`. Bare `/dashboard` opens the role's home (forecaster → control-room, operations → live-data, analyst → verification, admin → governance, auditor → audit) |

## Structure

```
src/
├── App.tsx                    Router (landing / login / dashboard), auth redirects (in effects)
├── context/VarunaContext.tsx  Global state: region, variable, lead, regime, role, theme, sidebar,
│                              summary + forecast package fetches, measured benchmark, route ↔ URL sync
├── services/api.ts            API client + offline demo fixtures   · services/auth.ts  JWT login/logout
├── services/platform.ts       Live data, notifications, verify-run, audit, governance, users
├── utils/models.ts            Labels/colours for every model slot (classic + live), time formatting
├── pages/LiveDataPage.tsx     Data sources (India-first): IMD grid read/upload, NCMRWF scan, IMD API, global fetch, backfill
├── components/layout/         Navbar (compact; account menu shows the fixed role), ContextBar (filters, wraps), NotificationBell, Sidebar, CommandPalette
├── components/shared/         Traceable (hover/click explanation of any number), PipelineTrace (clickable 14 stages,
│                              stage-14 verify + skill memory), SourceModeBadge, trust bars, upload modal, …
├── components/drawers/        Fusion trace, region detail, failure simulation
├── components/maps/           IndiaMetMap (always-dark canvas, theme-aware overlays)
└── pages/                     One file per dashboard page
```

## Data honesty rules

- `SourceModeBadge` shows where the numbers came from: **NCMRWF/IMD** (authorised Indian feed), **NCMRWF/IMD + GLOBAL MODELS**, **GLOBAL MODELS OVER INDIA**, **STORED DATA**, **SYNTHETIC DEMO SCENARIO**, or **OFFLINE DEMO** (backend unreachable). The context bar's default data mode is *Auto (India-first)*. `data_mode` only means "backend reachable".
- Wrap any displayed forecast number in `<Traceable field=… model=…>` so its formula and sources are one hover away; never type numbers into components.
- Controls are shown only when the signed-in user's permission list (from `/auth/login`) allows the action (`can('data:ingest')` etc.); the API enforces the same matrix.
- No decorative pulsing / pinging; animation is reserved for loading state.
- Benchmark numbers come from `GET /api/verification/compare|summary` — never hard-code skill claims in components.
- Wrong passwords are rejected; the offline demo session is created only when the API cannot be reached.
- The role is fixed to the signed-in account; there is no role switcher. A different role needs a separate account created by an administrator (AUDITOR is a separate read-only track). Backend `ANALYST` ↔ UI `MODEL_ANALYST` are normalised in `VarunaContext`.

## Theming (light & dark)

The theme is a class on `<html>` (`dark` or none), saved in `localStorage` (`varuna_theme`), defaulting to the OS preference and applied before first paint by a script in `index.html`.

Use **semantic tokens**, not raw palette shades, for anything that sits on a surface:

| Use | Class |
|---|---|
| Page / card backgrounds | `bg-surface`, `bg-surface-container-low … -highest`, `bg-surface-deep` |
| Primary / secondary text | `text-on-surface`, `text-on-surface-variant` |
| Accent | `text-primary`, `bg-primary`, `text-secondary`, `text-tertiary`, `text-error` |
| Borders | `border-surface-border`, `border-outline-variant` |
| Status colours | pair both modes: `text-emerald-600 dark:text-emerald-400`, `bg-amber-50 dark:bg-amber-950/40` |

Avoid `text-slate-100…400`, `text-cyan-300/400` or `bg-*-950` without a `dark:` pair — they are invisible or muddy in light mode. Tokens are CSS variables defined in `src/index.css` for `:root` (light) and `html.dark, .dark` (dark). Adding `className="dark"` to an element makes a dark-theme island (used by the map canvas). Typography tokens from `public/assets/varuna/DESIGN.md` are available as `text-headline-*`, `text-body-*`, `text-label-*`, `text-data-*`.
