# 🍁 Maple Store — AI Department

**A demonstration pilot of an AI Department that continuously monitors the
fragmented Indian pre-owned iPhone market and recommends optimal buy & sell
prices.** Investor/demo ready, runnable locally with mock data, and built to
extend into production.

> The Indian pre-owned iPhone market is fragmented across 15+ platforms, prices
> move daily, condition grading is inconsistent, and buy-back prices are opaque.
> Maple's AI Department turns all of that into a **single source of truth**.

![Architecture](docs/architecture.svg)

---

## What it does

Six specialist agents run continuously over the market and feed five
investor-grade dashboards:

| Agent | Job |
|---|---|
| 🛰️ **Competitor Intelligence** | Tracks lowest/median price, premium vs value sellers, price movement, and a platform × series heatmap across Cashify, ControlZ, OLX, Quikr, Facebook, Apple Trade-In, Dubai resale. |
| 💰 **Market Pricing** | Computes a condition-normalized fair value (weighted average · recency · condition weighting) and recommends **buy & sell** prices for every grade. |
| 🔍 **Device Pricing** | Breaks every device down **by site**: per-platform lowest/median/highest, spread vs fair value, condition mix, and the full listing feed with all publicly-scrapable detail (colour, battery, warranty, accessories, seller rating, lock status). |
| 🔀 **Arbitrage** | Finds buy-low/sell-high spreads across Indian cities (e.g. *Hyderabad ₹82.9k → Mumbai ₹95.1k, +14.8%*) and totals the opportunity value. |
| 📦 **Inventory** | Surfaces high-demand models, underpriced acquisition targets, oversupplied stock and coverage gaps, with pricing recommendations. |
| ⇄ **Dubai Expansion** | Compares India vs Dubai prices, computes landed-cost margin after duty, and scores export opportunities. |
| ⚖ **Maple vs Market** | Compares Maple's OWN store prices (scraped from maplestore.in) against market fair value & competitor median per device, and decomposes the premium Maple charges into what's *justified* (certification + warranty + trust). |
| 🤖 **ML Pricing** | A lightweight scikit-learn model (gradient boosting + one-hot) learned from the live market: fair value with confidence, learned condition/city/platform effects, a depreciation curve and a short forecast. An *additive* second opinion alongside the formula engine. |

### The six dashboards
- **Executive** — market index + movement, headline buy/sell recommendation, KPI strip, top arbitrage, demand & underpriced.
- **Competitor** — rankings, pricing heatmap, median-by-platform, 60-day trend.
- **Device Pricing** — searchable device picker, per-site price table, median-by-site chart, buy/sell-by-condition, and a full per-listing detail feed.
- **Maple vs Market** — Maple's own price vs market fair value & competitor median per device, premium % + verdict, the justification breakdown, and the ML Price-Intelligence panel (depreciation curve + forecast).
- **Dubai Expansion** — India⇄Dubai spreads, export table, margin waterfall.
- **Inventory** — demand signals, buy/sell recommendations, underpriced & oversupplied, gaps.

### Data modes — mock vs real
The pilot runs in two interchangeable modes, selected with **`MAPLE_DATA_SOURCE`**:

| Mode | What it is | Index | Use |
|---|---|---|---|
| `mock` *(default)* | Deterministic synthetic market from a committed fixture. | Pinned **96.43** | Reliable, offline, byte-identical demo. |
| `real` | Maple's real catalogue scraped from **maplestore.in** (Shopify JSON) + best-effort competitors (mock fallback), snapshotted to a committed fixture. | Computed from real data | The live story. |

The active mode is shown as a badge in the header ("MOCK DATA" / "REAL DATA"). Maple's
own listings are tracked as an `own`-role source and are **excluded from the competitor
benchmark** (the client isn't its own competitor). Rebuild the real snapshot any time with
`make build-real-fixture` (re-scrapes + retrains the ML model).

---

## Quickstart

### Docker (full stack: Postgres · Redis · API · Worker · Frontend)
```bash
cd maple-pilot
docker compose up --build
# Dashboards  → http://localhost:3000
# API + docs  → http://localhost:8000/docs
```

### Local (no Docker — SQLite, fastest demo)
```bash
# Terminal 1 — backend
cd maple-pilot/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# MOCK data (default, offline, deterministic):
MAPLE_AS_OF=2026-06-11 MAPLE_DATA_SOURCE=mock uvicorn app.main:app --port 8000
# …or REAL scraped data (loads the committed real fixture):
# MAPLE_AS_OF=2026-06-16 MAPLE_DATA_SOURCE=real uvicorn app.main:app --port 8000
# (or simply `make backend` / `make backend-real`)

# Terminal 2 — frontend
cd maple-pilot/frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

Full instructions, config and troubleshooting: **[docs/SETUP.md](docs/SETUP.md)**.

---

## Sample output (live mock market, seed 42, as-of 2026-06-11)

```
Maple Used-iPhone Index ........ 96.43   (1d +0.24% · 7d +0.16% · 30d −1.84%)
Headline: iPhone 16 Pro Max 256GB → BUY ₹88,390 / SELL ₹1,05,628 (FMV ₹97,804)
Top arbitrage .................. iPhone 16 Pro Max 256GB · Hyderabad→Mumbai +14.8% (₹49k)
Arbitrage value surfaced ....... ₹5.5L / month
Dubai .......................... iPhone 16 Pro 128GB · India ₹73k vs Dubai ₹55.3k → ₹9.6k net
```

**Board KPIs**

| Metric | Result |
|---|---|
| Gross Margin Lift | **+3.0 pts** (11% → 14%, ≈ ₹22.6L/mo) |
| Inventory Turn Improvement | **+40%** (6.0 → 8.4 turns/yr) |
| Purchase Accuracy | **74% → 87%** |
| Pricing Accuracy | **79% → 90%** |
| Missed Opportunity Reduction | **91%** |
| Market Coverage | **100%** of the priced catalogue |
| Arbitrage Opportunity Value | **₹5.8L / month** |

---

## Scope

- **Models:** iPhone 13 · 14 · 15 · 16 · 17 series — **70 SKUs**
- **Variants:** Base · Plus · Pro · Pro Max · Mini (13 series)
- **Storage:** 128GB · 256GB · 512GB · 1TB
- **Maple Condition System:** Almost New › Superb › Good › Fair
- **Geographies:** 10 Indian cities + 3 UAE cities

### Condition normalization (configurable)
Competitor grades map into Maple's four grades:

| Competitor says | Maple grade |
|---|---|
| Mint / Like New / Pristine / Open Box / A+ | **Almost New** |
| Excellent / Superb / Very Good | **Superb** |
| Good / Fine | **Good** |
| Fair / Average / Acceptable / C | **Fair** |

Mapping lives in `backend/app/config.py` (`DEFAULT_GRADE_MAP`) and is overridable
via `maple_config.json`.

---

## Pricing Recommendation Formula

```
Recommended Selling Price =
    Market Median + Brand Premium + Warranty Premium + Maple Trust Premium

Recommended Buying Price =
    Recommended Selling Price
    − Target Margin − Refurbishment Cost − Logistics Cost − Warranty Reserve
```

**Every variable is configurable** (`config.PricingConfig`). Defaults: brand 1.5%,
warranty 3.5%, trust 3.0%, target margin 14%, refurb ₹1,200, logistics ₹450,
warranty reserve ₹800.

Fair value itself is a weighted, recency- and condition-aware, outlier-trimmed
central estimate — see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind · Recharts |
| Backend | Python · FastAPI · SQLAlchemy |
| Database | PostgreSQL (SQLite-compatible for local) |
| Queue | Redis + worker (synchronous fallback) |
| Scraping | **Scrapling** (HTTP `Fetcher` for Shopify JSON · `StealthyFetcher` for bot-protected sites) · mock fallback |
| ML | scikit-learn (gradient boosting + one-hot) · joblib artifact |
| Deploy | Docker + Docker Compose |

---

## Project structure

```
maple-pilot/
├── backend/
│   └── app/
│       ├── config.py          # all configurable business rules
│       ├── catalog.py         # iPhone 13–17 universe + MSRP/depreciation
│       ├── normalization.py   # competitor grade → Maple grade
│       ├── pricing.py         # fair value + recommendation formula
│       ├── mock_data.py       # internally-consistent market generator
│       ├── metrics.py         # board KPIs
│       ├── models.py / db.py / seed.py
│       ├── scrapers/          # 8 adapters (incl. maplestore.in) + resilient base
│       ├── agents/            # 8 agents (incl. Maple-compare + ML) + orchestrator
│       ├── ml/                # scikit-learn pricing model (features · model · train)
│       ├── api/               # FastAPI routers
│       └── workers/           # Redis queue + worker
├── frontend/
│   ├── app/                   # 5 dashboards (App Router)
│   ├── components/            # Shell, charts, heatmap, UI kit
│   └── lib/                   # api client, hooks, formatting
├── docs/                      # ARCHITECTURE · API · SETUP · diagram
└── docker-compose.yml
```

---

## Extending to production

The architecture is built to grow:

1. **Live scraping is wired** — `MAPLE_DATA_SOURCE=real` already scrapes Maple's
   own catalogue (maplestore.in Shopify JSON, via Scrapling). Competitor adapters
   attempt a real `StealthyFetcher` scrape and fall back to mock per-platform;
   harden each `fetch_raw()` (and run `python -m camoufox fetch` once for the
   stealth browser) to take them fully live. Mock fallback stays as a safety net.
2. **Add platforms** — drop a new `BaseScraper` subclass and register it; add a
   `PlatformConfig` row. Agents pick it up automatically.
3. **Schedule** — the Redis worker already consumes a `refresh_market` job; wire
   it to cron / a scheduler for a continuous cadence.
4. **Real grades & history** — replace the mock generator; the schema, agents and
   dashboards are unchanged.
5. **Tune economics** — edit `maple_config.json`; no code changes.

---

## Deliverables

- ✅ Full source code (backend + frontend)
- ✅ Database schema (`backend/app/models.py`)
- ✅ Docker setup (`docker-compose.yml`, per-service Dockerfiles)
- ✅ Mock dataset (`python -m scripts.export_mock_dataset`)
- ✅ Pre-built DB fixture, loaded on startup (`backend/app/fixtures/seed_market.json`, rebuild with `make build-fixture`)
- ✅ API documentation (`docs/API.md` + live `/docs`)
- ✅ Setup guide (`docs/SETUP.md`)
- ✅ Architecture diagram (`docs/architecture.svg` + mermaid)
- ✅ Sample dashboards (four, live with mock data)
- ✅ README (this file)

---

*Demo pilot v1.0 — runnable locally with mock data, ready to extend into production.*
