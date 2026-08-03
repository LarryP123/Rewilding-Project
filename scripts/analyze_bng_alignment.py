from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import CANONICAL_SCORES_PATH
from src.features import add_bng_opportunity_score, add_distance_to_habitat_feature

SCENARIOS = ["scenario_nature_first", "scenario_balanced", "scenario_low_conflict"]
DEFAULT_URBAN_CODES = ("111", "112", "121")  # CORINE: continuous/discontinuous urban fabric, industrial/commercial


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test whether registered BNG site placement tracks ecological "
            "opportunity (this model's scenario scores) or proximity to "
            "existing urban/industrial land (a proxy for where development, "
            "and therefore offset demand, already exists). Writes one "
            "timestamped JSON record per run, appended to a tracking log, "
            "so this can be rerun periodically as the register grows."
        ),
    )
    parser.add_argument("--scores-path", type=Path, default=CANONICAL_SCORES_PATH)
    parser.add_argument("--bng-path", type=Path, default=Path("data/raw/reference/bng_gain_sites.geojson"))
    parser.add_argument(
        "--corine-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km_v6/corine_england_subset.parquet"),
        help="CORINE land cover subset used as the urban/industrial-land proxy.",
    )
    parser.add_argument("--urban-codes", nargs="+", default=list(DEFAULT_URBAN_CODES))
    parser.add_argument(
        "--out-path",
        type=Path,
        default=Path("outputs/bng_alignment_tracking.jsonl"),
        help="Tracking log; one JSON record is appended per run.",
    )
    parser.add_argument("--tile-size-m", type=float, default=50_000)
    return parser.parse_args()


def share_within(distance_m, km_thresholds):
    km = distance_m / 1000
    return {f"within_{t}km_pct": round((km <= t).mean() * 100, 1) for t in km_thresholds}


def main() -> None:
    args = parse_args()
    for path in (args.scores_path, args.bng_path, args.corine_path):
        if not path.exists():
            raise SystemExit(f"{path} does not exist.")

    scored = gpd.read_parquet(args.scores_path)
    bng = gpd.read_file(args.bng_path)
    corine = gpd.read_parquet(args.corine_path)
    urban = corine[corine["code_18"].astype(str).isin(args.urban_codes)].copy()

    enriched = add_bng_opportunity_score(scored, bng, tile_size_m=args.tile_size_m)
    enriched = add_distance_to_habitat_feature(
        enriched, urban, feature_name="distance_to_urban_m", tile_size_m=args.tile_size_m
    )

    record: dict = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "bng_site_count": int(len(bng)),
        "hex_count": int(len(enriched)),
    }

    record["national_baseline"] = share_within(enriched["distance_to_bng_site_m"], [5, 10, 20])

    record["scenario_correlations"] = {}
    record["scenario_top100"] = {}
    for scenario in SCENARIOS:
        corr = enriched[[scenario, "bng_opportunity_score_raw"]].corr().iloc[0, 1]
        record["scenario_correlations"][scenario] = round(float(corr), 3)
        top100 = enriched.sort_values(scenario, ascending=False).head(100)
        record["scenario_top100"][scenario] = share_within(top100["distance_to_bng_site_m"], [5, 10, 20])

    urban_bng_corr = enriched[["distance_to_urban_m", "distance_to_bng_site_m"]].corr().iloc[0, 1]
    urban_balanced_corr = enriched[["distance_to_urban_m", "scenario_balanced"]].corr().iloc[0, 1]
    record["urban_proximity_test"] = {
        "corr_distance_to_urban_vs_distance_to_bng": round(float(urban_bng_corr), 3),
        "corr_distance_to_urban_vs_scenario_balanced": round(float(urban_balanced_corr), 3),
    }

    bng_proj = bng.to_crs(enriched.crs)
    bng_to_urban = gpd.sjoin_nearest(
        bng_proj[["geometry"]], urban[["geometry"]], how="left", distance_col="dist_to_urban_m"
    )
    hex_centroids = scored[["hex_id", "geometry"]].copy()
    hex_centroids["geometry"] = hex_centroids.geometry.centroid
    hex_to_urban = gpd.sjoin_nearest(
        hex_centroids, urban[["geometry"]], how="left", distance_col="dist_to_urban_m"
    )
    record["urban_proximity_test"]["bng_sites"] = share_within(bng_to_urban["dist_to_urban_m"], [1, 2, 5, 10])
    record["urban_proximity_test"]["national_hexes"] = share_within(hex_to_urban["dist_to_urban_m"], [1, 2, 5, 10])
    record["urban_proximity_test"]["bng_sites"]["mean_km"] = round(bng_to_urban["dist_to_urban_m"].mean() / 1000, 2)
    record["urban_proximity_test"]["national_hexes"]["mean_km"] = round(hex_to_urban["dist_to_urban_m"].mean() / 1000, 2)

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    with args.out_path.open("a") as f:
        f.write(json.dumps(record) + "\n")

    print(json.dumps(record, indent=2))
    print()
    print(f"appended to: {args.out_path}")


if __name__ == "__main__":
    main()
