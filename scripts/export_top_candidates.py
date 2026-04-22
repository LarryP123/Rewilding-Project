from __future__ import annotations

import argparse
from pathlib import Path
import sys

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import CANONICAL_SCORES_PATH
from src.geography import attach_geography_name, summarize_named_geography
from src.provenance import score_provenance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export top-ranked rewilding candidate hexes from a scored layer.",
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=CANONICAL_SCORES_PATH,
        help="Path to the scored hex layer.",
    )
    parser.add_argument(
        "--scenario",
        default="scenario_balanced",
        choices=[
            "scenario_nature_first",
            "scenario_balanced",
            "scenario_low_conflict",
        ],
        help="Scenario column used for ranking.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="Number of top hexes to export.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/top_candidates_1km"),
        help="Directory for CSV, GeoJSON, and summary outputs.",
    )
    parser.add_argument(
        "--lnrs-path",
        type=Path,
        default=Path("data/raw/reference/lnrs_boundaries.geojson"),
        help="Optional LNRS geography used to add policy-area names and slices.",
    )
    parser.add_argument(
        "--lnrs-name-column",
        type=str,
        default=None,
        help="Optional LNRS name column override.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gdf = gpd.read_parquet(args.scores_path)
    provenance = score_provenance(gdf, args.scores_path)
    ranked = gdf.sort_values(args.scenario, ascending=False).head(args.top_n).copy()
    ranked = attach_geography_name(
        ranked,
        args.lnrs_path,
        join_key="hex_id",
        output_column="lnrs_name",
        name_column=args.lnrs_name_column,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.scenario}_top_{args.top_n}"

    csv_path = args.out_dir / f"{stem}.csv"
    geojson_path = args.out_dir / f"{stem}.geojson"
    summary_path = args.out_dir / f"{stem}_summary.md"

    ranked.drop(columns="geometry").to_csv(csv_path, index=False)
    ranked.to_file(geojson_path, driver="GeoJSON")

    top_columns = [
        "hex_id",
        "lnrs_name",
        args.scenario,
        "cell_area_ratio",
        "undersized_cell_penalty",
        "priority_habitat_share",
        "connectivity_score",
        "restoration_opportunity_score",
        "biodiversity_observation_score_raw",
        "bird_species_richness",
        "bird_record_count",
        "mammal_species_richness",
        "mammal_record_count",
        "habitat_mosaic_score",
        "agri_opportunity_score_raw",
    ]
    top_columns = [column for column in top_columns if column in ranked.columns]

    summary = [
        f"# Top Candidates: {args.scenario}",
        "",
        f"Source layer: `{args.scores_path}`",
        f"Run profile: `{provenance['run_profile']}`",
        f"Flood source: `{provenance['flood_feature_source']}` from `{provenance['flood_source_path'] or 'not recorded'}`",
        f"Peat source: `{provenance['peat_feature_source']}` from `{provenance['peat_source_path'] or 'not recorded'}`",
        f"Rows exported: {len(ranked)}",
        "",
        "## Score summary",
        "",
        ranked[[args.scenario]].describe().round(2).to_string(),
        "",
        "## Top 10 hexes",
        "",
        ranked[top_columns].head(10).round(2).to_string(index=False),
    ]

    lnrs_summary = summarize_named_geography(
        ranked,
        name_column="lnrs_name",
        score_column=args.scenario,
    )
    if not lnrs_summary.empty:
        summary.extend(
            [
                "",
                "## LNRS slice summary",
                "",
                lnrs_summary.rename(columns={"lnrs_name": "lnrs"}).round(2).to_string(index=False),
            ]
        )

    summary_path.write_text("\n".join(summary) + "\n")

    print(f"csv: {csv_path}")
    print(f"geojson: {geojson_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
