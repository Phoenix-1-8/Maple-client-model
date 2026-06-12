"""The Maple AI Department — five specialist agents + an orchestrator."""
from .arbitrage import ArbitrageAgent  # noqa: F401
from .competitor import CompetitorIntelligenceAgent  # noqa: F401
from .dubai import DubaiExpansionAgent  # noqa: F401
from .inventory import InventoryAgent  # noqa: F401
from .market_pricing import MarketPricingAgent  # noqa: F401
from .orchestrator import AGENTS, executive_snapshot, run_agent  # noqa: F401
