from __future__ import annotations

import argparse
from pathlib import Path
import sys

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export top-ranked rewilding candidate hexes from a scored layer.",
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary/hex_scores.parquet"),
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
        default=Path("outouts/top_candidates"),
        help="Directory for CSV, GeoJSON, and summary outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gdf = gpd.read_parquet(args.scores_path)
    ranked = gdf.sort_values(args.scenario, ascending=False).head(args.top_n).copy()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.scenario}_top_{args.top_n}"

    csv_path = args.out_dir / f"{stem}.csv"
    geojson_path = args.out_dir / f"{stem}.geojson"
    summary_path = args.out_dir / f"{stem}_summary.md"

    ranked.drop(columns="geometry").to_csv(csv_path, index=False)
    ranked.to_file(geojson_path, driver="GeoJSON")

    top_columns = [
        "hex_id",
        args.scenario,
        "cell_area_ratio",
        "undersized_cell_penalty",
        "priority_habitat_share",
        "connectivity_score",
        "restoration_opportunity_score",
        "habitat_mosaic_score",
        "agri_opportunity_score_raw",
    ]
    top_columns = [column for column in top_columns if column in ranked.columns]

    summary = [
        f"# Top Candidates: {args.scenario}",
        "",
        f"Source layer: `{args.scores_path}`",
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

    summary_path.write_text("\n".join(summary) + "\n")

    print(f"csv: {csv_path}")
    print(f"geojson: {geojson_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
