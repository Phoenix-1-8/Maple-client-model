"""
Export the mock dataset to CSV + JSON (deliverable: 'Mock dataset').

Usage (from backend/):
    python -m scripts.export_mock_dataset           # writes to ./mock_dataset/
    python -m scripts.export_mock_dataset --out /path
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.config import get_config
from app.mock_data import build_rng, generate_history, generate_listings
from app.util import as_of_date


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="mock_dataset")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cfg = get_config()
    as_of = as_of_date()
    rng = build_rng(cfg)

    listings = generate_listings(cfg, as_of, rng)
    market_daily, device_daily = generate_history(cfg, as_of, rng)

    # listings.csv
    fields = list(listings[0].keys()) if listings else []
    with (out / "listings.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in listings:
            r = dict(row)
            r["listing_date"] = r["listing_date"].isoformat()
            w.writerow(r)

    # JSON snapshots
    (out / "listings.json").write_text(
        json.dumps(
            [{**l, "listing_date": l["listing_date"].isoformat()} for l in listings],
            indent=2,
        )
    )
    (out / "market_index.json").write_text(
        json.dumps([{**m, "day": m["day"].isoformat()} for m in market_daily], indent=2)
    )

    print(f"Wrote {len(listings)} listings, {len(market_daily)} index days to {out}/")
    print(" -", out / "listings.csv")
    print(" -", out / "listings.json")
    print(" -", out / "market_index.json")


if __name__ == "__main__":
    main()
