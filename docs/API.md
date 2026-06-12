# API Reference

Base URL: `http://localhost:8000/api`
Interactive docs (Swagger): `http://localhost:8000/docs`
All responses are JSON. All money is INR unless a `currency` field says otherwise.

---

## Meta & control

### `GET /health`
```json
{ "status": "ok", "service": "maple-ai-department" }
```

### `GET /config`
Returns the active, configurable business rules: `pricing`, `baselines`,
`condition_multipliers`, `condition_confidence`, `maple_grades`, `aed_to_inr`,
`platforms`, `city_multipliers`.

### `GET /normalization/grades`
The competitor-grade → Maple-grade mapping.
```json
{ "maple_grades": ["Almost New","Superb","Good","Fair"],
  "mapping": [ { "competitor_grade": "mint", "maple_grade": "Almost New" }, ... ] }
```

### `GET /catalog`
The full iPhone 13–17 device universe with MSRPs and launch dates (70 SKUs).

### `GET /scrape/sources`
Lists each scraper, its base URL, region and whether BrightData is enabled.

### `POST /scrape/refresh`
Re-runs every scraper (live → mock fallback) and replaces current listings.
Returns a per-platform report with `source: "live" | "mock"`.
```json
{ "refreshed": true, "total_listings": 1200, "live_listings": 0, "mock_listings": 1200,
  "platforms": [ { "platform": "cashify", "source": "mock", "count": 185 }, ... ] }
```

### `POST /seed?force=true`
Wipes and regenerates the full mock market (listings + 60-day history).

---

## Market

### `GET /market/index`
The Maple Used-iPhone Index time series (base 100).
```json
{ "latest": { "day": "2026-06-11", "index": 96.43, "movement_pct": 0.24, "active_listings": 1213 },
  "history": [ { "day": "...", "index": 100.0, "movement_pct": 0.0, "active_listings": 0 }, ... ] }
```

### `GET /market/snapshot`
Cross-agent summary that powers the Executive Dashboard: `market_index`,
`market_index_history`, `headline_device`, `top_arbitrage`, `top_dubai`,
`top_demand`, `top_underpriced`, `competitor_rankings`.

### `GET /market/metrics`
The board-level KPIs.
```json
{ "headline": {
    "gross_margin_lift_pts": 3.0, "gross_margin_lift_value_monthly": 2257732,
    "inventory_turn_improvement_pct": 40.0,
    "purchase_accuracy_before": 74.0, "purchase_accuracy_after": 87.2,
    "pricing_accuracy_before": 79.0, "pricing_accuracy_after": 89.7,
    "missed_opportunity_reduction_pct": 91.0, "market_coverage_pct": 100.0,
    "arbitrage_opportunity_value_monthly": 576220 },
  "detail": { ... } }
```

### `GET /market/pricing?region=IN&series=16`
Recommended buy/sell for every device & grade (optionally filtered by series).
```json
{ "device_count": 70, "devices": [ {
    "sku": "ip16-promax-256gb", "model": "iPhone 16 Pro Max", "storage": "256GB",
    "fair_value": 97804, "confidence": 0.95,
    "recommendations": { "Superb": {
        "market_median": 97804, "brand_premium": 1467, "warranty_premium": 3423,
        "maple_trust_premium": 2934, "recommended_sell": 105628,
        "target_margin": 14788, "refurbishment_cost": 1200, "logistics_cost": 450,
        "warranty_reserve": 800, "recommended_buy": 88390,
        "expected_gross_margin_pct": 0.14 }, "Good": { ... }, ... } } ] }
```

### `GET /market/pricing/{sku}?region=IN`
The same recommendation block for a single SKU (404 if no data).

---

## Agents

### `GET /agents`
Lists the five agents.

### `GET /agents/competitor`
`market_lowest`, `market_median`, `competitor_rankings[]` (price_index, position,
listings, median), `premium_sellers`, `value_sellers`, `price_movement`,
`price_heatmap` (platform × series index matrix).

### `GET /agents/arbitrage?top_n=20`
```json
{ "opportunities_found": 35, "total_opportunity_value": 550395,
  "opportunities": [ { "model": "iPhone 16 Pro Max", "storage": "256GB",
     "buy_city": "Hyderabad", "buy_price": 82854, "sell_city": "Mumbai",
     "sell_price": 95097, "spread": 12243, "spread_pct": 14.8,
     "opportunity_value": 48974, "city_prices": { ... } } ] }
```

### `GET /agents/inventory?region=IN`
`kpis`, `high_demand[]`, `underpriced[]`, `oversupplied[]`, `inventory_gaps[]`.

### `GET /agents/dubai?top_n=20`
```json
{ "devices_compared": 37, "viable_opportunities": 6, "total_margin_potential": 25825,
  "aed_to_inr": 23.0, "import_duty_pct": 18.0, "cross_border_logistics": 1500,
  "opportunities": [ { "model": "iPhone 16 Pro", "storage": "128GB",
     "india_value": 73000, "dubai_cost": 55334, "dubai_cost_aed": 2406,
     "spread_pct": 31.9, "landed_cost": 66794, "maple_sell": 78840,
     "net_margin": 9596, "margin_pct": 12.2, "export_opportunity_score": 19.5,
     "direction": "Source in Dubai → sell in India" } ] }
```

---

## Listings

### `GET /listings?platform=&sku=&series=&city=&condition=&region=&limit=100&offset=0`
Paginated raw listings with all normalized fields.

### `GET /listings/facets`
Counts grouped `by_platform`, `by_city`, `by_condition`, `by_region`,
`by_series` — powers filters and the heatmap.
