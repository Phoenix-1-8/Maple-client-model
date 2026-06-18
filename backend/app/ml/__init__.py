"""Lightweight ML pricing layer (scikit-learn).

An *additive* statistical model that learns used-iPhone price from the market
listings and produces the numbers the dashboards show — fair value, learned
condition / city / platform effects, a depreciation curve and a short forecast —
without replacing the deterministic formula engine in ``pricing.py``.
"""
from .model import PriceModel, load_model, MODEL_PATH

__all__ = ["PriceModel", "load_model", "MODEL_PATH"]
