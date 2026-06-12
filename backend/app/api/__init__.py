"""API routers."""
from fastapi import APIRouter

from . import agents, listings, market, meta

api_router = APIRouter()
api_router.include_router(meta.router, tags=["meta"])
api_router.include_router(market.router, tags=["market"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(listings.router, tags=["listings"])
