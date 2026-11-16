# Reachly

A small CRM for cold outreach. Track businesses you contact (name, phone, optional email and website, type, city, channel, status, notes), schedule meetings, and export everything to Excel.

Built for one user: log in, work through a list of prospects, move them through the pipeline.

## Features
- **Dashboard** with status tabs (New → Contacted → Replied → Meeting scheduled → Proposal sent → Won / Lost)
- Search and filters: name/phone, city, business type, **"No website"** (handy for finding clients who need one)
- Inline status change, **Select** mode with edit / bulk delete, notes and reminders column
- **Schedule** meetings with a date picker and time; see all of them on the Meetings page
- Phone is required; email and website are optional and validated when present
- JWT login (plus optional sign-up, off by default), light and dark theme
- Excel export of businesses, meetings and a summary sheet

## Stack
| Part | Tech |
|---|---|
| Client | React 19, Vite, Tailwind v4, shadcn/ui (Base UI), HeroUI calendar and forms, Geist font |
| API | FastAPI, Pydantic, psycopg2, PyJWT, bcrypt |
| Database | PostgreSQL, Alembic migrations |
| Export | pandas + openpyxl |
| Tooling | [uv](https://docs.astral.sh/uv/) (Python), [just](https://just.systems) (tasks), pytest |

## Project layout
```
backend/    FastAPI app, auth, validators, db helpers, Alembic migrations
client/     React app (src/components/ui = shadcn components)
scripts/    export_xlsx.py
tests/      pytest suite (separate test database)
justfile    all common commands
DEPLOYMENT.md   deployment plan
```

## Setup
1. Install [uv](https://docs.astral.sh/uv/), [just](https://just.systems), Node 20+ and PostgreSQL.
2. `cp .env.example .env` and fill it in (see below).
3. `just install`
4. `just db-setup` (creates the database and applies migrations)
5. `just create-user you@example.com` (prompts for a password, min 8 characters)
6. `just dev` for backend and client together, or `just backend` and `just client` in two terminals.
   - App: http://localhost:5173
   - API docs: http://localhost:4000/docs

## Environment (`.env`)
| Variable | Meaning |
|---|---|
| `DATABASE_URL` | `postgresql://user:password@localhost:5432/outreach_crm` |
| `SECRET_KEY` | 32+ random characters: `python -c "import secrets;print(secrets.token_urlsafe(64))"` |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | token lifetime, default `60` |
| `ALLOW_SIGNUP` | `true` shows a working sign-up form; keep `false` on anything reachable by others |

## Commands (`just` lists all)
| Command | What it does |
|---|---|
| `just dev` | backend + client together |
| `just backend` / `just client` | run one side |
| `just migrate` / `just rollback` | apply / undo migrations |
| `just migration "message"` | new migration file |
| `just create-user EMAIL` | create or update a login |
| `just export [file.xlsx]` | export to Excel |
| `just test` | run the test suite |

## API overview
All `/api` routes except `/api/auth/login` and `/api/auth/signup` need `Authorization: Bearer <token>`.

- `POST /api/auth/login`, `POST /api/auth/signup`, `GET /api/auth/me`
- `GET/POST /api/businesses`, `PUT/DELETE /api/businesses/{id}`, `POST /api/businesses/bulk-delete`
- `GET /api/meetings`, `POST /api/businesses/{id}/meetings`, `PATCH/DELETE /api/meetings/{id}`

Full interactive docs at `/docs` while running locally.

## Notes
- Business data is personal contact information; keep the database private and back it up.
- See `DEPLOYMENT.md` before putting this on the internet.
