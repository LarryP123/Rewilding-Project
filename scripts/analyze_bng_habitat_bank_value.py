"""Score hexes for BNG habitat bank value, not just ecological opportunity.

This models the actual mechanics of the Statutory Biodiversity Metric 4.0,
not just a generic proximity signal:

- The spatial risk multiplier (SRM) gives a habitat bank full value (1.0)
  to developments in the SAME Local Planning Authority (LPA) or National
  Character Area (NCA), a reduced value (0.75) to NEIGHBOURING LPA/NCA, and
  half value (0.5) everywhere else. A site's addressable market is
  therefore its own LPA/NCA plus their immediate neighbours.
- The strategic significance multiplier gives a 1.15x uplift to habitat
  parcels that a published Local Nature Recovery Strategy (LNRS) has
  formally mapped as a "potential measure" location. This script only has
  a coarse proxy for that (whether the hex falls inside a supplied LNRS
  boundary at all) — the real rule requires the specific mapped measure to
  match the proposed habitat, which needs LNRS Local Habitat Map data this
  script does not have. Treat this component as directional, not
  compliance-grade.

market_accessibility_score approximates "addressable demand": the amount
of existing urban/industrial land (a proxy for where development, and
therefore BNG obligations, already concentrate — validated in
analyze_bng_alignment.py) within a hex's own LPA/NCA, plus a discounted
contribution from neighbouring LPA/NCAs, mirroring the SRM tiers.

habitat_yield_score reuses the existing restoration_opportunity_score as a
proxy for achievable distinctiveness/condition uplift. It is not a real
Metric 4.0 unit calculation (that requires a specified target habitat type
and a full baseline/post-intervention run) — this is a screening signal,
not a substitute for a real biodiversity metric assessment.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import CANONICAL_SCORES_PATH
from src.geography import attach_geography_name, find_neighbouring_polygons
from src.score import minmax_scale

NEIGHBOUR_DISCOUNT = 0.75  # Metric 4.0 spatial risk multiplier for neighbouring LPA/NCA
STRATEGIC_SIGNIFICANCE_UPLIFT = 1.15  # Metric 4.0 "high" strategic significance multiplier
URBAN_CODES = ("111", "112", "121")  # CORINE: continuous/discontinuous urban fabric, industrial/commercial


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Score hexes for BNG habitat bank value: achievable habitat "
            "yield combined with market accessibility modelled on the "
            "Metric 4.0 spatial risk multiplier's LPA/NCA tiers."
        ),
    )
    parser.add_argument("--scores-path", type=Path, default=CANONICAL_SCORES_PATH)
    parser.add_argument(
        "--lpa-path",
        type=Path,
        default=Path("data/raw/reference/local_planning_authorities.geojson"),
    )
    parser.add_argument(
        "--nca-path",
        type=Path,
        default=Path("data/raw/reference/national_character_areas.geojson"),
    )
    parser.add_argument(
        "--corine-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km_v6/corine_england_subset.parquet"),
    )
    parser.add_argument(
        "--lnrs-path",
        type=Path,
        default=Path("data/raw/reference/lnrs_boundaries.geojson"),
        help="Optional. Coarse proxy only — see module docstring.",
    )
    parser.add_argument(
        "--yield-weight",
        type=float,
        default=0.5,
        help="Weight on habitat_yield_score in the composite; market_accessibility_score gets the remainder.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/bng_habitat_bank_value"))
    parser.add_argument("--top-n", type=int, default=25)
    return parser.parse_args()


def demand_by_region(regions: gpd.GeoDataFrame, name_column: str, urban: gpd.GeoDataFrame) -> pd.Series:
    """Sum urban/industrial land area (km^2) within each named region."""
    overlap = gpd.overlay(regions[[name_column, "geometry"]], urban[["geometry"]], how="intersection")
    if overlap.empty:
        return pd.Series(0.0, index=regions[name_column])
    overlap["area_km2"] = overlap.geometry.area / 1_000_000
    demand = overlap.groupby(name_column)["area_km2"].sum()
    return demand.reindex(regions[name_column]).fillna(0.0)


def accessibility_from_region(
    region_names: pd.Series,
    demand: pd.Series,
    neighbours: dict[str, set[str]],
) -> pd.Series:
    own = region_names.map(demand).fillna(0.0)

    def neighbour_component(name: object) -> float:
        if pd.isna(name):
            return 0.0
        neighbour_names = neighbours.get(name, set())
        if not neighbour_names:
            return 0.0
        values = [demand.get(n, 0.0) for n in neighbour_names]
        return sum(values) / len(values)

    neighbour_values = region_names.map(neighbour_component)
    return own + neighbour_values * NEIGHBOUR_DISCOUNT


def main() -> None:
    args = parse_args()
    for path in (args.scores_path, args.lpa_path, args.nca_path, args.corine_path):
        if not path.exists():
            raise SystemExit(f"{path} does not exist.")

    scored = gpd.read_parquet(args.scores_path)

    lpa = gpd.read_file(args.lpa_path)
    lpa = lpa[lpa["LPA23CD"].astype(str).str.startswith("E")].copy()
    lpa = lpa.to_crs(scored.crs) if lpa.crs != scored.crs else lpa

    nca = gpd.read_file(args.nca_path)
    nca = nca.to_crs(scored.crs) if nca.crs != scored.crs else nca

    corine = gpd.read_parquet(args.corine_path)
    urban = corine[corine["code_18"].astype(str).isin(URBAN_CODES)].copy()

    print("attaching LPA and NCA membership...")
    enriched = attach_geography_name(scored, args.lpa_path, join_key="hex_id", output_column="lpa_name", name_column="LPA23NM")
    enriched = attach_geography_name(enriched, args.nca_path, join_key="hex_id", output_column="nca_name", name_column="NCA_Name")

    print("computing development demand per LPA and NCA...")
    lpa_demand = demand_by_region(lpa, "LPA23NM", urban)
    nca_demand = demand_by_region(nca, "NCA_Name", urban)

    print("finding neighbouring LPAs and NCAs...")
    lpa_neighbours = find_neighbouring_polygons(lpa, "LPA23NM")
    nca_neighbours = find_neighbouring_polygons(nca, "NCA_Name")

    lpa_accessibility = accessibility_from_region(enriched["lpa_name"], lpa_demand, lpa_neighbours)
    nca_accessibility = accessibility_from_region(enriched["nca_name"], nca_demand, nca_neighbours)
    # Metric 4.0 counts a site as "within" if it matches on LPA OR NCA, so a
    # hex's addressable market is the better of the two routes in, not the sum.
    raw_accessibility = pd.concat([lpa_accessibility, nca_accessibility], axis=1).max(axis=1)
    enriched["market_accessibility_score"] = minmax_scale(raw_accessibility).fillna(0.0)

    enriched["habitat_yield_score"] = enriched["restoration_opportunity_score"]

    strategic_multiplier = pd.Series(1.0, index=enriched.index)
    if args.lnrs_path.exists():
        with_lnrs = attach_geography_name(enriched, args.lnrs_path, join_key="hex_id", output_column="_lnrs_name")
        strategic_multiplier = with_lnrs["_lnrs_name"].notna().map(
            {True: STRATEGIC_SIGNIFICANCE_UPLIFT, False: 1.0}
        )
        print(f"LNRS strategic-significance proxy applied ({args.lnrs_path}).")
    else:
        print(f"No LNRS boundary supplied ({args.lnrs_path} not found) — strategic significance left neutral (1.0).")
    enriched["strategic_significance_multiplier"] = strategic_multiplier

    composite = (
        args.yield_weight * enriched["habitat_yield_score"]
        + (1 - args.yield_weight) * enriched["market_accessibility_score"]
    ) * enriched["strategic_significance_multiplier"]
    enriched["bng_habitat_bank_value_score"] = composite.clip(upper=100 * STRATEGIC_SIGNIFICANCE_UPLIFT).round(2)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    scored_path = args.out_dir / "hex_scores_bng_habitat_bank_value.parquet"
    enriched.to_parquet(scored_path)

    top = enriched.sort_values("bng_habitat_bank_value_score", ascending=False).head(args.top_n)
    top_cols = [
        "hex_id", "lpa_name", "nca_name", "habitat_yield_score",
        "market_accessibility_score", "strategic_significance_multiplier",
        "bng_habitat_bank_value_score",
    ]
    print()
    print(top[top_cols].to_string(index=False))

    lpa_rollup = (
        enriched.groupby("lpa_name", as_index=False)
        .agg(
            hex_count=("hex_id", "count"),
            mean_value_score=("bng_habitat_bank_value_score", "mean"),
            max_value_score=("bng_habitat_bank_value_score", "max"),
            mean_accessibility=("market_accessibility_score", "mean"),
        )
        .sort_values("mean_value_score", ascending=False)
    )
    lpa_rollup_path = args.out_dir / "lpa_rollup.csv"
    lpa_rollup.to_csv(lpa_rollup_path, index=False)

    print()
    print(f"hex-level output: {scored_path}")
    print(f"LPA rollup: {lpa_rollup_path}")
    print()
    print("Top 10 LPAs by mean BNG habitat bank value score:")
    print(lpa_rollup.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
