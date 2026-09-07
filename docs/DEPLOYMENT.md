# Local deployment guide

## Prerequisites

- Docker Desktop with Docker Compose, or Python 3.11+ and Node.js 22+.
- Ports 4173, 8000, and 5432 available.

## Docker path

From the repository root:

```powershell
docker-compose up --build
```

Wait for PostgreSQL to become healthy, then open `http://127.0.0.1:4173`. API documentation is at `http://127.0.0.1:8000/docs`. Stop with `docker-compose down`; add `-v` only when deliberately deleting the demo database.

## Native developer path

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:ASGP_DATABASE_URL = "sqlite+pysqlite:///./asgp.db"
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open `http://127.0.0.1:5173`. For a non-default API location set `VITE_API_URL` before building the frontend. Never expose the prototype directly to the public internet; production authentication and hardened secret management are intentionally outside MVP scope.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests sdk\tests
.\.venv\Scripts\python.exe -m ruff check backend sdk
cd frontend
pnpm build
pnpm lint
```
