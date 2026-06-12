"""
Maple Store — AI Department API.

FastAPI service exposing the market-intelligence brain:
  * scrapers + mock fallback
  * 5 specialist agents
  * pricing recommendations & KPIs

On startup it ensures the schema exists and seeds a full mock market so the
whole pilot is live immediately (investor-demo ready).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config import get_config
from .seed import seed_on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    try:
        result = seed_on_startup()
        print(f"[startup] {result}")
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] seeding failed: {exc}")
    yield


def create_app() -> FastAPI:
    cfg = get_config()
    app = FastAPI(
        title="Maple Store — AI Department",
        description=(
            "Continuous market intelligence for the Indian pre-owned iPhone "
            "market: competitor tracking, fair-value pricing, arbitrage, "
            "inventory signals and Dubai expansion."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Respect the configured allowlist. Set CORS_ORIGINS=* for allow-all.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cfg.infra.cors_origins if o.strip()],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=cfg.infra.api_prefix)

    @app.get("/")
    def root() -> dict:
        return {
            "service": "Maple Store AI Department",
            "docs": "/docs",
            "api_prefix": cfg.infra.api_prefix,
            "health": f"{cfg.infra.api_prefix}/health",
        }

    return app


app = create_app()
