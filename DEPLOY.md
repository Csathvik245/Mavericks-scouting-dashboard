# Deploying (Render + Vercel)

Backend (Flask API) → **Render**. Frontend (Vite SPA) → **Vercel**. They're
independent; deploy the backend first so you have its URL for the frontend.

The app runs **entirely from a committed, pre-seeded `backend/cache.db`** in
production (`OFFLINE_CACHE=1`). It never calls `stats.nba.com` — which blocks
datacenter IPs and would hang on Render, whose filesystem is also ephemeral.
Re-seed only when you change `SEASON` (see the bottom of this file).

---

## 1. Backend on Render

Either point Render at this repo as a **Blueprint** (it reads [`render.yaml`](render.yaml)),
or create a **Web Service** manually with:

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120` |

**Environment variables (Render):**

| Var | Value | Required | Notes |
|---|---|---|---|
| `OFFLINE_CACHE` | `1` | **Yes** | Serve the committed cache; never hit stats.nba.com. |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app` | **Yes** | Your Vercel URL. Comma-separate multiple; `*` allows all (fine for a demo). |
| `PYTHON_VERSION` | `3.12.4` | Recommended | Pin so pandas/numpy wheels resolve. |
| `SEASON` | `2025-26` | No | Only if different from the default. |
| `WEB_CONCURRENCY` | `1` | No | Gunicorn worker count. Free tier is 512 MB — pandas is heavy, keep it at 1–2. |

`$PORT` is provided by Render automatically — don't set it.

---

## 2. Frontend on Vercel

Import the repo; Vercel auto-detects Vite. Set:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework Preset | Vite (auto) |
| Build Command | `npm run build` (auto) |
| Output Directory | `dist` (auto) |

**Environment variable (Vercel):**

| Var | Value | Notes |
|---|---|---|
| `VITE_API_BASE` | `https://<your-render-service>.onrender.com` | Your Render URL, **no trailing slash**. |

> ⚠️ `VITE_API_BASE` is inlined at **build time**, not runtime. If you change it,
> you must **redeploy** the frontend for it to take effect.

Routing is hash-based (`#team`, `#player/<id>`), so no SPA rewrite rules are needed —
refreshes and deep links work out of the box.

---

## 3. Order of operations (avoids a CORS chicken-and-egg)

1. Deploy the **backend** on Render (`OFFLINE_CACHE=1`, `CORS_ORIGINS=*` for now). Note its URL.
2. Deploy the **frontend** on Vercel with `VITE_API_BASE=<render URL>`. Note its URL.
3. Set `CORS_ORIGINS=<vercel URL>` on Render and redeploy the backend (tighten from `*`).

---

## Re-seeding the cache (only when SEASON changes)

The committed `cache.db` is a snapshot of the default season. To refresh it (run
locally, where stats.nba.com is reachable):

```bash
cd backend
python seed_cache.py --force            # or --season 2024-25
git add cache.db && git commit -m "Re-seed cache"
```

Then redeploy. Don't run `seed_cache.py` on Render — the live pull will fail there.
