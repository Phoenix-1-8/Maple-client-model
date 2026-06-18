# Maple Store AI Department — convenience targets

.PHONY: up down backend backend-real frontend seed refresh dataset build-fixture build-real-fixture train-model install-backend install-frontend

# ---- Docker ----
up:            ## Build & run the full stack
	docker compose up --build

down:          ## Stop and remove volumes
	docker compose down -v

# ---- Local backend (SQLite) ----
install-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

backend:       ## Run the API locally with MOCK data (port 8000)
	cd backend && . .venv/bin/activate && MAPLE_AS_OF=2026-06-11 MAPLE_DATA_SOURCE=mock uvicorn app.main:app --reload --port 8000

backend-real:  ## Run the API locally with REAL scraped data (port 8000)
	cd backend && . .venv/bin/activate && MAPLE_AS_OF=2026-06-16 MAPLE_DATA_SOURCE=real uvicorn app.main:app --reload --port 8000

# ---- Local frontend ----
install-frontend:
	cd frontend && npm install

frontend:      ## Run the dashboards locally (port 3000)
	cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev

# ---- Data ----
seed:          ## Force-reseed the mock market
	curl -X POST "http://localhost:8000/api/seed?force=true"

refresh:       ## Re-scrape (mock fallback) and replace listings
	curl -X POST "http://localhost:8000/api/scrape/refresh"

dataset:       ## Export the mock dataset to backend/mock_dataset/
	cd backend && . .venv/bin/activate && python -m scripts.export_mock_dataset --out mock_dataset

build-fixture: ## Rebuild the committed MOCK DB fixture (app/fixtures/seed_market.json)
	cd backend && . .venv/bin/activate && python -m scripts.build_seed_fixture

build-real-fixture: ## Scrape live sources -> committed REAL fixture + ML model
	cd backend && . .venv/bin/activate && python -m scripts.build_real_fixture

train-model:   ## Re-train the ML pricing model from the seeded DB (mode via MAPLE_DATA_SOURCE)
	cd backend && . .venv/bin/activate && python -m app.ml.train
