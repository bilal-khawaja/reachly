set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# install everything (python via uv, client via npm)
install:
    uv sync
    npm --prefix client install

# run FastAPI backend with reload on :4000 (docs at /docs)
backend:
    uv run uvicorn main:app --app-dir backend --reload --port 4000

alias api := backend

# run backend + client together
dev:
    npm run dev

# run React client on :5173
client:
    npm --prefix client run dev

# create the database if missing, then apply all migrations
db-setup: db-create migrate

db-create:
    uv run python backend/create_db.py

# apply migrations up to head
migrate:
    uv run alembic upgrade head

# roll back one migration
rollback:
    uv run alembic downgrade -1

# create a new empty migration: just migration "add foo column"
migration message:
    uv run alembic revision -m "{{message}}"

# show current migration revision / history
current:
    uv run alembic current

history:
    uv run alembic history --verbose

# create/update login user: just create-user me@example.com
create-user email:
    uv run python backend/create_user.py {{email}}

# export businesses + meetings to xlsx (optional path)
export path="":
    uv run python scripts/export_xlsx.py {{path}}

test:
    uv run pytest
