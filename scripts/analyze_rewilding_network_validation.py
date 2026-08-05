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
from src.features import add_rewilding_network_proximity_score

SCENARIOS = ["scenario_nature_first", "scenario_balanced", "scenario_low_conflict"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the model against real, independently-chosen rewilding "
            "sites (the Rewilding Network) rather than a policy register: "
            "does this model's opportunity score rediscover places "
            "practitioners have already chosen, or rank them no better than "
            "chance? These locations were never used to build or weight the "
            "model, so this is a genuine held-out check, not a circular one."
        ),
    )
    parser.add_argument("--scores-path", type=Path, default=CANONICAL_SCORES_PATH)
    parser.add_argument(
        "--projects-path",
        type=Path,
        default=Path("data/raw/reference/rewilding_network_projects.geojson"),
    )
    parser.add_argument(
        "--boundary-path",
        type=Path,
        default=Path("data/raw/boundaries/england_boundary.parquet"),
    )
    parser.add_argument(
        "--out-path",
        type=Path,
        default=Path("outputs/rewilding_network_validation.json"),
    )
    parser.add_argument("--tile-size-m", type=float, default=50_000)
    return parser.parse_args()


def share_within(distance_m, km_thresholds):
    km = distance_m / 1000
    return {f"within_{t}km_pct": round((km <= t).mean() * 100, 1) for t in km_thresholds}


def main() -> None:
    args = parse_args()
    for path in (args.scores_path, args.projects_path, args.boundary_path):
        if not path.exists():
            raise SystemExit(f"{path} does not exist.")

    scored = gpd.read_parquet(args.scores_path)
    boundary = gpd.read_parquet(args.boundary_path)

    projects = gpd.read_file(args.projects_path)
    if projects.crs is None:
        projects = projects.set_crs("EPSG:4326")

    total_projects = len(projects)
    hidden_mask = projects["hideExactLocation"].fillna(False) if "hideExactLocation" in projects.columns else False
    visible = projects[~hidden_mask].copy()

    boundary_wgs84 = boundary.to_crs(projects.crs) if boundary.crs != projects.crs else boundary
    england_projects = gpd.sjoin(visible, boundary_wgs84[["geometry"]], how="inner", predicate="within").drop(
        columns=["index_right"]
    )
    england_projects = england_projects.to_crs(scored.crs)

    enriched = add_rewilding_network_proximity_score(scored, england_projects, tile_size_m=args.tile_size_m)

    record: dict = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "rewilding_network_total_sites_britain": int(total_projects),
        "rewilding_network_hidden_location_sites": int(total_projects - len(visible)),
        "rewilding_network_england_sites_used": int(len(england_projects)),
        "hex_count": int(len(enriched)),
    }

    record["national_baseline"] = share_within(enriched["distance_to_rewilding_project_m"], [5, 10, 20])

    record["scenario_correlations"] = {}
    record["scenario_top100"] = {}
    for scenario in SCENARIOS:
        corr = enriched[[scenario, "rewilding_network_proximity_score_raw"]].corr().iloc[0, 1]
        record["scenario_correlations"][scenario] = round(float(corr), 3)
        top100 = enriched.sort_values(scenario, ascending=False).head(100)
        record["scenario_top100"][scenario] = share_within(top100["distance_to_rewilding_project_m"], [5, 10, 20])

    # The core validation question: for the hex nearest each real project,
    # what percentile does it fall at nationally, per scenario? A model that
    # rediscovers real sites should skew well above the 50th percentile.
    record["nearest_hex_percentiles"] = {}
    for scenario in SCENARIOS:
        percentiles = enriched[scenario].rank(pct=True) * 100
        enriched_with_pct = enriched.assign(_pct=percentiles)

        # nearest hex to each individual project (not deduplicated by distance value)
        proj_nearest = gpd.sjoin_nearest(
            england_projects[["geometry"]], enriched_with_pct[["hex_id", "_pct", "geometry"]], how="left"
        )
        pct_values = proj_nearest["_pct"]
        record["nearest_hex_percentiles"][scenario] = {
            "mean_percentile": round(float(pct_values.mean()), 1),
            "median_percentile": round(float(pct_values.median()), 1),
            "pct_in_top_10_percent": round(float((pct_values >= 90).mean() * 100), 1),
            "pct_in_top_25_percent": round(float((pct_values >= 75).mean() * 100), 1),
            "pct_below_median": round(float((pct_values < 50).mean() * 100), 1),
        }

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    args.out_path.write_text(json.dumps(record, indent=2) + "\n")

    print(json.dumps(record, indent=2))
    print()
    print(f"written to: {args.out_path}")


if __name__ == "__main__":
    main()
