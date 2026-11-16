# Reachly: deployment plan

Goal: test locally for a few days, then deploy as one small app (FastAPI + built React + Postgres) for a single user.

## Phase 0: local testing (now, ~3-5 days)

Use it for real outreach and keep a list of what is missing.

- [ ] Run it the way production will: build the client and serve it from FastAPI (see Phase 1), not through the Vite dev server.
- [ ] Set `ALLOW_SIGNUP=false` in `.env` and log in with the user from `just create-user`.
- [ ] Add real businesses, change statuses, schedule meetings, run `just export`.
- [ ] Note friction (missing columns, slow flows, bugs). Fix the top 3, then deploy.
- [ ] Back up your local DB once with `pg_dump` and restore it into a scratch DB, to prove backups work.

Exit criteria: you used it for several days, no data-losing bugs, `just test` is green.

## Phase 1: code changes needed for production

| # | Change | Why | Where |
|---|--------|-----|-------|
| 1 | Serve the built React app from FastAPI | In dev, Vite proxies `/api`. In prod there is no Vite. One service, one domain, no CORS | `backend/main.py`: mount `client/dist` with `StaticFiles(html=True)` after the `/api` routes |
| 2 | Make CORS configurable | Currently hard-coded to `http://localhost:5173`. Same-origin prod needs none | `backend/main.py`: read `CORS_ORIGINS` env var, default empty |
| 3 | Hide interactive docs in prod | `/docs` and `/openapi.json` expose the whole API | `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` when `ENV=production` |
| 4 | Rate-limit login | `/api/auth/login` can be brute-forced | e.g. `slowapi`, 5/min per IP |
| 5 | Security headers | Basic hardening | middleware for `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS (or let the host/proxy add them) |
| 6 | Health endpoint | The host needs a liveness check | `GET /api/health` returning `{"ok": true}` (also checks DB) |
| 7 | Run migrations on deploy | Schema must match code | start command: `alembic upgrade head && uvicorn ...` |
| 8 | Dockerfile (multi-stage) | Repeatable build | stage 1: `npm ci && npm run build` in `client/`; stage 2: Python + `uv sync --no-dev`, copy `dist`; run `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| 9 | Fix `.gitignore` and init git | Not a git repo yet. `.venv`, `client/dist`, `exports` must not be committed | add `.venv/`, `client/dist/`, `.env*` except `.env.example` |
| 10 | Pin deps and remove stray ones | The unrelated npm `cn` package keeps being re-added by shadcn; `react-day-picker` and the shadcn `calendar.jsx` are now unused | `npm rm cn react-day-picker`, delete `components/ui/calendar.jsx` |
| 11 | Remove the "Backend not running" dev hint from prod | The message refers to `just backend` | `client/src/api.js`: generic message when `import.meta.env.PROD` |
| 12 | Token storage | JWT lives in `localStorage` | acceptable for a single-user tool behind HTTPS; optional upgrade is an httpOnly cookie |

Optional later: a `/api/auth/change-password` endpoint, an audit of the `just create-user` flow for first-user bootstrap.

## Phase 2: configuration (production env vars)

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | provided by the managed Postgres |
| `SECRET_KEY` | **new** random 64+ chars (`python -c "import secrets; print(secrets.token_urlsafe(64))"`). Never reuse the local one |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` (or shorter) |
| `ALLOW_SIGNUP` | `false` |
| `ENV` | `production` |

Create your account on the server with `just create-user` equivalent (one-off command in the host's shell), then keep signup off.

## Phase 3: hosting options

Pick one; all handle Docker + managed Postgres.

- **Railway / Render**: easiest. App + Postgres add-on, automatic HTTPS, deploy from git. About $5-10/month.
- **Fly.io**: cheap and fast, a bit more CLI work (`fly launch`, `fly postgres`).
- **Small VPS (Hetzner/DigitalOcean) + Caddy**: cheapest at scale and the most control, but you manage updates and backups.

My default: **Railway or Render**, because HTTPS, backups and deploys come built in.

## Phase 4: deploy steps

1. `git init`, fix `.gitignore`, first commit, push to a private GitHub repo.
2. Create the Postgres instance; copy its `DATABASE_URL`.
3. Create the web service from the repo/Dockerfile; set the env vars from Phase 2.
4. First deploy runs `alembic upgrade head`.
5. Open a shell on the service and create your user.
6. Visit the URL: confirm HTTPS, log in, add a business, schedule a meeting.
7. Confirm `/docs` returns 404 and `/api/auth/signup` returns 403.

## Phase 5: after go-live

- [ ] Turn on automatic daily DB backups; test a restore once.
- [ ] Add uptime monitoring (UptimeRobot or the host's checks) on `/api/health`.
- [ ] Custom domain (optional) with automatic TLS.
- [ ] `just export` against production data (run locally pointing `DATABASE_URL` at prod, read-only if possible).
- [ ] Rotate `SECRET_KEY` if it was ever shared or leaked (this logs everyone out).

## Risks to keep in mind

- **Leads are personal/business contact data.** Keep the DB private, backups encrypted, and don't make the service public beyond login.
- **Single user.** Signup stays off; if a second person ever needs access, create them with the CLI.
- **Free tiers sleep or wipe.** Use a paid plan with persistent Postgres for real data.
