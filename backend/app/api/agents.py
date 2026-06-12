"""Endpoints for each specialist agent."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..agents.arbitrage import ArbitrageAgent
from ..agents.competitor import CompetitorIntelligenceAgent
from ..agents.dubai import DubaiExpansionAgent
from ..agents.inventory import InventoryAgent
from ..agents.orchestrator import AGENTS
from ..db import get_session

router = APIRouter()


@router.get("/agents")
def list_agents() -> dict:
    return {
        "agents": [
            {"name": name, "title": cls.title} for name, cls in AGENTS.items()
        ]
    }


@router.get("/agents/competitor")
def competitor(db: Session = Depends(get_session)) -> dict:
    return CompetitorIntelligenceAgent().run(db)


@router.get("/agents/arbitrage")
def arbitrage(top_n: int = Query(20), db: Session = Depends(get_session)) -> dict:
    return ArbitrageAgent().run(db, top_n=top_n)


@router.get("/agents/inventory")
def inventory(region: str = Query("IN"), db: Session = Depends(get_session)) -> dict:
    return InventoryAgent().run(db, region=region)


@router.get("/agents/dubai")
def dubai(top_n: int = Query(20), db: Session = Depends(get_session)) -> dict:
    return DubaiExpansionAgent().run(db, top_n=top_n)
