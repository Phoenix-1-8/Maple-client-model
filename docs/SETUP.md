# Setup Guide

Two ways to run the pilot. **Option A (Docker)** is closest to production.
**Option B (local)** is the fastest for a laptop demo and needs no Docker.

---

## Option A — Docker (Postgres + Redis + API + Worker + Frontend)

Prerequisites: Docker + Docker Compose.

```bash
cd maple-pilot
docker compose up --build
```

Then open:

| Service | URL |
|---|---|
| Dashboards | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| API health | http://localhost:8000/api/health |

On first boot the backend loads a **pre-built market fixture committed to the
repo** (`backend/app/fixtures/seed_market.json`) into Postgres — so every
machine gets the exact same, fully-populated demo with no runtime data
generation. The worker shares that database and waits for queued jobs.

To stop and wipe data:
```bash
docker compose down -v
```

---

## Option B — Local (no Docker)

Prerequisites: Python 3.11+ and Node 18+.

### 1. Backend (SQLite, zero services)

```bash
cd maple-pilot/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API comes up at http://localhost:8000 and populates `maple.db` (SQLite)
from the same committed fixture used by Docker, so the local and Docker demos
are identical. For a fully reproducible demo, pin the date:

```bash
MAPLE_AS_OF=2026-06-11 uvicorn app.main:app --port 8000
```

> **Pre-built data fixture.** Seeding loads `app/fixtures/seed_market.json`
> instead of generating data at runtime. To regenerate it (after changing the
> catalog, config, or generator), run `make build-fixture` (or
> `python -m scripts.build_seed_fixture`). To force on-the-fly generation
> instead of the fixture, set `MAPLE_SEED_SOURCE=generate`.

> Live scraping is optional and **not wired in this pilot** — scrapers always
> fall back to deterministic mock data, so nothing extra is needed for the demo.
> To enable it: implement `fetch_raw()` in each adapter (a Playwright skeleton is
> in `app/scrapers/cashify.py`), then `pip install playwright &&
> python -m playwright install chromium` and set `BRIGHTDATA_WSS`.

### 2. Frontend

```bash
cd maple-pilot/frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

Open http://localhost:3000.

---

## Common tasks

**Reseed / refresh the market** (from the UI, click **Refresh market**, or):
```bash
curl -X POST http://localhost:8000/api/scrape/refresh
curl -X POST "http://localhost:8000/api/seed?force=true"
```

**Export the mock dataset** (CSV + JSON deliverable):
```bash
cd maple-pilot/backend
python -m scripts.export_mock_dataset --out mock_dataset
```

**Tune the business rules** — copy `backend/maple_config.example.json` to
`backend/maple_config.json` (or point `MAPLE_CONFIG_FILE` at it) and edit
premiums, costs, the grade map, city/platform indices, etc. Restart the API.

**Run with Postgres locally** (instead of SQLite):
```bash
export DATABASE_URL=postgresql+psycopg2://maple:maple@localhost:5432/maple
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard says "Is the backend running…" | Start the API; confirm `NEXT_PUBLIC_API_URL`. |
| Empty Dubai/arbitrage tables | Click **Refresh market** to regenerate listings. |
| Port already in use | Change `-p` (uvicorn) / `-p` (next dev) / compose port maps. |
| Want different numbers each run | Change `MAPLE_MOCK_SEED`. |
