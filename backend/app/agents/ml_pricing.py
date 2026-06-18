"""
ML Pricing Agent — serves the additive scikit-learn pricing layer.

Reads the committed model artifact (app/fixtures/price_model.joblib) and exposes
its outputs for the "Price Intelligence (ML)" view: per-SKU ML fair value with a
confidence, learned condition/city/platform effects, the depreciation curve, and
a short forecast. It degrades gracefully: if no model is trained, every endpoint
returns ``{"available": false, ...}`` and the UI falls back to the formula engine.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..catalog import device_by_sku, iphone_devices
from ..ml import load_model
from .base import Agent


class MLPricingAgent(Agent):
    name = "ml_pricing"
    title = "ML Pricing Agent"

    def _unavailable(self) -> dict:
        return {
            "agent": self.title,
            "available": False,
            "reason": "No trained model artifact. Build it with `python -m app.ml.train`.",
        }

    def overview(self, db: Session, region: str = "IN") -> dict:
        model = load_model()
        if model is None:
            return self._unavailable()

        devices = []
        for dev in iphone_devices():
            fv = model.fair_value(dev.sku)
            if not fv:
                continue
            devices.append({
                "sku": dev.sku,
                "model": dev.model,
                "variant": dev.variant,
                "storage": dev.storage,
                "series": dev.series,
                "ml_fair_value": round(fv),
                "confidence": model.confidence(dev.sku),
            })
        devices.sort(key=lambda d: (d["series"], d["ml_fair_value"]))
        return {
            "agent": self.title,
            "available": True,
            "model": {
                "kind": "GradientBoostingRegressor + one-hot (log-price)",
                "metrics": model.metrics,
                "monthly_depreciation_pct": round((2.718281828 ** model.depr_k - 1) * 100, 2),
                "value_platforms": [k for k, _ in model.value_platforms],
                "as_of": model.as_of.isoformat(),
            },
            "depreciation_curve": model.depreciation_curve(),
            "device_count": len(devices),
            "devices": devices,
        }

    def price_one(self, db: Session, sku: str, region: str = "IN") -> dict | None:
        model = load_model()
        if device_by_sku(sku) is None:
            return None
        if model is None:
            return self._unavailable()
        fv = model.fair_value(sku)
        if not fv:
            return None
        return {
            "agent": self.title,
            "available": True,
            "sku": sku,
            "ml_fair_value": round(fv),
            "confidence": model.confidence(sku),
            "condition_effects": model.condition_effects(sku),
            "city_effects": model.city_effects(sku),
            "platform_effects": model.platform_effects(sku),
            "forecast": model.forecast(sku),
        }

    def forecast_all(self, db: Session, region: str = "IN") -> dict:
        model = load_model()
        if model is None:
            return self._unavailable()
        points = []
        for dev in iphone_devices():
            f = model.forecast(dev.sku)
            if not f:
                continue
            last = f["points"][-1]
            points.append({
                "sku": dev.sku,
                "model": dev.model,
                "storage": dev.storage,
                "current_fair_value": f["current_fair_value"],
                "projected_30d": last["projected_fair_value"],
                "change_pct": last["change_pct"],
            })
        points.sort(key=lambda d: d["change_pct"])
        return {
            "agent": self.title,
            "available": True,
            "monthly_depreciation_pct": round((2.718281828 ** model.depr_k - 1) * 100, 2),
            "horizon_days": 30,
            "devices": points,
        }

    # Orchestrator entrypoint.
    def run(self, db: Session, region: str = "IN") -> dict:
        return self.overview(db, region=region)
