"""
Train the ML pricing model and persist the artifact.

The model learns from the COMPETITOR market (Maple's own-store listings are
excluded — the model estimates the market Maple is measured against). It can be
trained from the live database or from an in-memory list of listings (used by
the real-fixture build, before anything is in the DB).

Usage (from backend/):
    python -m app.ml.train                # train from the seeded DB
"""
from __future__ import annotations

from datetime import date

from ..config import MapleConfig, get_config
from ..util import as_of_date
from .model import PriceModel, model_path_for, reset_model_cache, save_model


def train_from_listings(
    listings, as_of: date | None = None, cfg: MapleConfig | None = None,
    path=None, save: bool = True,
) -> PriceModel:
    """Train on an in-memory listing list (own-store rows should be pre-filtered)."""
    cfg = cfg or get_config()
    as_of = as_of or as_of_date()
    path = path or model_path_for(cfg.infra.data_source)
    model = PriceModel.train(listings, as_of, cfg=cfg)
    if save:
        save_model(model, path)
        reset_model_cache()
    return model


def train_from_db(path=None) -> PriceModel:
    """Train from the seeded database (competitor listings, region IN)."""
    from ..agents.base import Agent  # local import: avoids heavy import at module load
    from ..db import SessionLocal

    cfg = get_config()
    as_of = as_of_date()
    path = path or model_path_for(cfg.infra.data_source)
    with SessionLocal() as db:
        # include_own defaults False -> Maple own-store rows excluded.
        listings = Agent(cfg).load_listings(db, region="IN")
    return train_from_listings(listings, as_of=as_of, cfg=cfg, path=path)


def main() -> None:
    model = train_from_db()
    print(f"[ml-train] wrote {model_path_for(get_config().infra.data_source)}")
    print(f"[ml-train] metrics: {model.metrics}")
    print(f"[ml-train] value platforms: {[k for k, _ in model.value_platforms]}")


if __name__ == "__main__":
    main()
