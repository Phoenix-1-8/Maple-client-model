# Maple Store AI Department — convenience targets

.PHONY: up down backend frontend seed refresh dataset build-fixture install-backend install-frontend

# ---- Docker ----
up:            ## Build & run the full stack
	docker compose up --build

down:          ## Stop and remove volumes
	docker compose down -v

# ---- Local backend (SQLite) ----
install-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

backend:       ## Run the API locally (port 8000)
	cd backend && . .venv/bin/activate && MAPLE_AS_OF=2026-06-11 uvicorn app.main:app --reload --port 8000

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

build-fixture: ## Rebuild the committed pre-built DB fixture (app/fixtures/seed_market.json)
	cd backend && . .venv/bin/activate && python -m scripts.build_seed_fixture
