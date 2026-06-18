"""
The ML pricing model — a lightweight, interpretable scikit-learn estimator.

``PriceModel`` wraps a one-hot + gradient-boosting pipeline that learns used
iPhone price from the market listings, then exposes the numbers the dashboards
want, all derived from the SAME fitted model:

    * fair_value(sku)        — market-blended value at the Superb/Delhi reference
    * condition_effects(sku) — learned grade multipliers (vs Superb)
    * city_effects(sku)      — learned geographic multipliers (arbitrage basis)
    * platform_effects(sku)  — learned per-platform price levels
    * depreciation_curve()   — retained value vs age (the "ML depreciation")
    * forecast(sku)          — short-horizon projection from the local age slope

It does NOT replace pricing.py — it's an additive, statistical second opinion.
Determinism: fixed ``random_state`` + a committed training fixture => stable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ..catalog import STORAGE_MULTIPLIER, device_age_months, device_by_sku
from ..config import MapleConfig, get_config
from .features import CATEGORICAL, FEATURES, NUMERIC, build_frame, row_for

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def model_path_for(data_source: str) -> Path:
    """Model artifact path per data mode (mock and real keep separate models)."""
    name = "price_model_real.joblib" if data_source == "real" else "price_model.joblib"
    return _FIXTURE_DIR / name


MODEL_PATH = model_path_for("mock")  # default (mock) path

REFERENCE_CONDITION = "Superb"
REFERENCE_CITY = "Delhi"
RANDOM_STATE = 42


@dataclass
class PriceModel:
    pipeline: Pipeline
    as_of: date
    competitor_platforms: list[tuple[str, float]]  # (key, weight), role != own
    value_platforms: list[tuple[str, float]]       # sell-side only (fair-value blend)
    cities: list[str]
    conditions: list[str]
    metrics: dict = field(default_factory=dict)
    # Fitted exponential depreciation: log(price/msrp) ≈ depr_b + depr_k * age_months.
    # depr_k is the monthly decay (negative); drives the forecast slope robustly
    # even where the gradient-boosting model is age-insensitive.
    depr_k: float = 0.0
    depr_b: float = 0.0

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #
    @classmethod
    def train(cls, listings, as_of: date, cfg: MapleConfig | None = None) -> "PriceModel":
        cfg = cfg or get_config()
        df = build_frame(listings, as_of)
        if len(df) < 30:
            raise ValueError(f"not enough rows to train ML model: {len(df)}")

        X = df[FEATURES]
        y = np.log1p(df["asking_price"].to_numpy())

        pre = ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
            remainder="passthrough",
        )
        model = GradientBoostingRegressor(
            n_estimators=300, max_depth=3, learning_rate=0.05,
            subsample=0.9, random_state=RANDOM_STATE,
        )
        pipe = Pipeline([("pre", pre), ("gb", model)])

        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)
        pipe.fit(Xtr, ytr)
        pred = np.expm1(pipe.predict(Xte))
        true = np.expm1(yte)
        metrics = {
            "r2": round(float(r2_score(true, pred)), 4),
            "mae": round(float(mean_absolute_error(true, pred)), 1),
            "mape": round(float(np.mean(np.abs((true - pred) / true)) * 100), 2),
            "n_train": int(len(Xtr)),
            "n_test": int(len(Xte)),
        }
        # Refit on the full dataset for the production artifact.
        pipe.fit(X, y)

        # Dedicated depreciation sub-fit: log(retained) ~ age (robust monthly decay).
        retained = (df["asking_price"] / df["msrp"]).clip(lower=1e-3)
        ages = df["age_months"].to_numpy()
        if ages.max() - ages.min() > 1e-6:
            depr_k, depr_b = np.polyfit(ages, np.log(retained.to_numpy()), 1)
        else:
            depr_k, depr_b = 0.0, float(np.log(retained.mean()))

        comp = [(p.key, p.weight) for p in cfg.competitor_platforms(region="IN")]
        # Sell-side platforms only for the fair-value blend (exclude trade-in,
        # which is a buy-side floor and would drag the value estimate down).
        value = [
            (p.key, p.weight)
            for p in cfg.competitor_platforms(region="IN")
            if p.role in ("recommerce", "marketplace")
        ]
        return cls(
            pipeline=pipe,
            as_of=as_of,
            competitor_platforms=comp,
            value_platforms=value or comp,
            cities=sorted(df["city"].unique().tolist()),
            conditions=[c for c in cfg.condition_multipliers if c in set(df["condition"])] or list(cfg.condition_multipliers),
            metrics=metrics,
            depr_k=float(depr_k),
            depr_b=float(depr_b),
        )

    # ------------------------------------------------------------------ #
    # Prediction primitives
    # ------------------------------------------------------------------ #
    def _predict_rows(self, rows: list[dict]) -> np.ndarray:
        X = pd.DataFrame(rows)[FEATURES]
        return np.expm1(self.pipeline.predict(X))

    def predict_price(
        self, sku: str, *, condition: str, city: str, platform: str,
        as_of: date | None = None, battery_health: int = 93,
    ) -> float | None:
        row = row_for(
            sku=sku, condition=condition, city=city, platform=platform,
            as_of=as_of or self.as_of, battery_health=battery_health,
        )
        if row is None:
            return None
        return float(self._predict_rows([row.as_dict()])[0])

    # ------------------------------------------------------------------ #
    # Dashboard outputs (all derived from the one fitted model)
    # ------------------------------------------------------------------ #
    def fair_value(self, sku: str, as_of: date | None = None) -> float | None:
        """Market-blended fair value at the Superb/Delhi reference.

        Weighted average of the model's prediction across every competitor
        platform (weights = config trust), so it reflects the market, not one site.
        """
        as_of = as_of or self.as_of
        rows, weights = [], []
        for key, w in self.value_platforms:
            r = row_for(sku=sku, condition=REFERENCE_CONDITION, city=REFERENCE_CITY,
                        platform=key, as_of=as_of)
            if r is not None:
                rows.append(r.as_dict())
                weights.append(w)
        if not rows:
            return None
        preds = self._predict_rows(rows)
        wsum = sum(weights) or 1.0
        return round(float(np.dot(preds, weights) / wsum), 0)

    def confidence(self, sku: str) -> float:
        """0..1 — anchored on model fit quality (R²), lightly device-agnostic."""
        r2 = self.metrics.get("r2", 0.5)
        return round(max(0.05, min(0.99, r2)), 2)

    def condition_effects(self, sku: str, as_of: date | None = None) -> dict[str, float]:
        as_of = as_of or self.as_of
        ref_key = self.competitor_platforms[0][0] if self.competitor_platforms else "cashify"
        base = self.predict_price(sku, condition=REFERENCE_CONDITION, city=REFERENCE_CITY,
                                  platform=ref_key, as_of=as_of)
        out: dict[str, float] = {}
        if not base:
            return out
        for cond in self.conditions:
            p = self.predict_price(sku, condition=cond, city=REFERENCE_CITY,
                                   platform=ref_key, as_of=as_of)
            if p:
                out[cond] = round(p / base, 3)
        return out

    def city_effects(self, sku: str, as_of: date | None = None) -> dict[str, float]:
        as_of = as_of or self.as_of
        ref_key = self.competitor_platforms[0][0] if self.competitor_platforms else "cashify"
        base = self.predict_price(sku, condition=REFERENCE_CONDITION, city=REFERENCE_CITY,
                                  platform=ref_key, as_of=as_of)
        out: dict[str, float] = {}
        if not base:
            return out
        for city in self.cities:
            p = self.predict_price(sku, condition=REFERENCE_CONDITION, city=city,
                                   platform=ref_key, as_of=as_of)
            if p:
                out[city] = round(p / base, 3)
        return out

    def platform_effects(self, sku: str, as_of: date | None = None) -> dict[str, float]:
        as_of = as_of or self.as_of
        fv = self.fair_value(sku, as_of)
        out: dict[str, float] = {}
        if not fv:
            return out
        for key, _w in self.competitor_platforms:
            p = self.predict_price(sku, condition=REFERENCE_CONDITION, city=REFERENCE_CITY,
                                   platform=key, as_of=as_of)
            if p:
                out[key] = round(p / fv, 3)
        return out

    def depreciation_curve(
        self, *, variant: str = "Pro", storage: str = "256GB",
        series_for_msrp: int = 16, months: int = 48, as_of: date | None = None,
    ) -> list[dict]:
        """Retained value (% of MSRP) vs age, read off the model.

        Uses a representative SKU and sweeps age by pretending the unit launched
        progressively earlier. Returns [{age_months, retained_pct, fair_value}].
        """
        as_of = as_of or self.as_of
        from ..catalog import Device

        dev = Device(series_for_msrp, variant, storage)
        if device_by_sku(dev.sku) is None:
            return []
        msrp = dev.msrp
        ref_key = self.competitor_platforms[0][0] if self.competitor_platforms else "cashify"
        storage_mult = STORAGE_MULTIPLIER.get(storage, 1.0)
        curve = []
        for age in range(0, months + 1, 3):
            row = {
                "series": series_for_msrp, "msrp": msrp, "age_months": float(age),
                "storage_mult": storage_mult, "battery_health": max(80, 100 - int(age * 0.3)),
                "variant": variant, "condition": REFERENCE_CONDITION,
                "city": REFERENCE_CITY, "platform": ref_key,
            }
            fv = float(self._predict_rows([row])[0])
            curve.append({
                "age_months": age,
                "fair_value": round(fv, 0),
                "retained_pct": round(fv / msrp, 4),
            })
        return curve

    def forecast(self, sku: str, *, horizons=(7, 14, 30), as_of: date | None = None) -> dict:
        """Short-horizon fair-value projection from the fitted depreciation decay.

        Projects the current fair value forward along the learned exponential
        decay (``depr_k`` per month). Used-market drift is gentle, so this reads
        as a credible near-term trajectory, not a volatility play.
        """
        as_of = as_of or self.as_of
        if device_by_sku(sku) is None:
            return {}
        fv_now = self.fair_value(sku, as_of)
        if not fv_now:
            return {}
        points = []
        for h in horizons:
            months = h / 30.44
            proj = fv_now * math.exp(self.depr_k * months)
            points.append({
                "horizon_days": h,
                "projected_fair_value": round(proj, 0),
                "change_pct": round((proj / fv_now - 1) * 100, 2),
            })
        return {
            "current_fair_value": fv_now,
            "monthly_drift_pct": round((math.exp(self.depr_k) - 1) * 100, 2),
            "points": points,
        }


# --------------------------------------------------------------------------- #
# Persistence + lazy loading
# --------------------------------------------------------------------------- #
def save_model(model: PriceModel, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


@lru_cache(maxsize=2)
def load_model(path: str | None = None) -> PriceModel | None:
    """Lazily load the committed model artifact; None if absent (graceful).

    With no explicit path, picks the artifact matching the active data mode
    (mock vs real) so each mode uses the model trained on its own data.
    """
    if path:
        p = Path(path)
    else:
        p = model_path_for(get_config().infra.data_source)
    if not p.exists():
        return None
    try:
        return joblib.load(p)
    except Exception:  # pragma: no cover - corrupt/incompatible artifact
        return None


def reset_model_cache() -> None:
    load_model.cache_clear()
