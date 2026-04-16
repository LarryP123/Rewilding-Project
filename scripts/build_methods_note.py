from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd


SCENARIO_LABELS = {
    "scenario_nature_first": "Nature-first restoration opportunity",
    "scenario_balanced": "Balanced restoration opportunity",
    "scenario_low_conflict": "Lower-conflict restoration opportunity",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a methods note for the canonical published run.",
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km_v4/hex_scores.parquet"),
        help="Path to the canonical scored hex layer.",
    )
    parser.add_argument(
        "--top-candidates-summary-path",
        type=Path,
        default=Path("outputs/top_candidates_1km/scenario_balanced_top_100_summary.md"),
        help="Optional shortlist summary path referenced in the note.",
    )
    parser.add_argument(
        "--cluster-summary-path",
        type=Path,
        default=Path("outputs/candidate_clusters/scenario_balanced_top_100_clusters_summary.md"),
        help="Optional cluster summary path referenced in the note.",
    )
    parser.add_argument(
        "--validation-summary-path",
        type=Path,
        default=Path("outputs/validation/validation_summary.md"),
        help="Optional validation summary path referenced in the note.",
    )
    parser.add_argument(
        "--app-path",
        type=Path,
        default=Path("outputs/app/rewilding_opportunity_explorer.html"),
        help="Optional packaged app path referenced in the note.",
    )
    parser.add_argument(
        "--out-path",
        type=Path,
        default=Path("outputs/methods.md"),
        help="Destination markdown file.",
    )
    return parser.parse_args()


def first_unique_value(frame: gpd.GeoDataFrame, column: str, fallback: str) -> str:
    if column not in frame.columns:
        return fallback
    values = frame[column].dropna().astype(str).unique().tolist()
    return values[0] if values else fallback


def scenario_block(scores: gpd.GeoDataFrame) -> list[str]:
    lines: list[str] = []
    for column, label in SCENARIO_LABELS.items():
        if column not in scores.columns:
            continue
        summary = scores[[column]].describe().round(2)
        lines.extend(
            [
                f"### {label}",
                "",
                summary.to_string(),
                "",
            ]
        )
    return lines


def maybe_reference(path: Path, label: str) -> str:
    return f"- {label}: `{path}`" if path.exists() else f"- {label}: not generated in this run"


def main() -> None:
    args = parse_args()
    scores = gpd.read_parquet(args.scores_path)

    cell_count = len(scores)
    flood_source = first_unique_value(scores, "flood_feature_source", "not recorded")
    peat_source = first_unique_value(scores, "peat_feature_source", "not recorded")
    bird_enabled = "bird_observation_score_raw" in scores.columns

    lines = [
        "# Methods Note",
        "",
        "## Purpose",
        "",
        "This project is a national screening and prioritisation workflow for rewilding in England.",
        "It combines a defined set of geospatial signals into comparable 1 km cell scores so England can be narrowed to plausible areas for closer review.",
        "This is a screening tool, not a causal model, not a site-selection engine, and not a site-level recommendation.",
        "",
        "## What This Run Does",
        "",
        "The canonical run turns habitat, bird-observation, agricultural, flood, and peat-related signals into three scenario views over the same national hex grid.",
        "Those scenario scores are then used to produce shortlist tables, candidate-zone summaries, validation outputs, and a standalone explorer.",
        "",
        "## What This Run Does Not Claim",
        "",
        "This run does not claim to identify final rewilding sites, predict ecological outcomes, model delivery feasibility, or replace local ecological and practical review.",
        "",
        "## Canonical Run",
        "",
        f"- Canonical scored layer: `{args.scores_path}`",
        f"- Cells scored: {cell_count:,}",
        "- Study area: England using the official England analysis boundary in British National Grid (`EPSG:27700`)",
        "- Analysis unit: 1 km hexagonal grid cells",
        "",
        "## Core Inputs In This Run",
        "",
        "- Habitat context from the locally prepared habitat proxy used in the MVP workflow",
        f"- Flood opportunity source recorded in the score layer: `{flood_source}`",
        f"- Peat opportunity source recorded in the score layer: `{peat_source}`",
        "- Agricultural opportunity from Agricultural Land Classification",
        (
            "- Bird observation opportunity from the observation-based bird indicator carried in this score layer"
            if bird_enabled
            else "- Bird observation opportunity was not present as a scored component in this layer"
        ),
        "",
        "## Scoring Logic",
        "",
        "Each input is transformed onto a common 0 to 100 interpretation so that higher values mean stronger apparent restoration opportunity.",
        "The repo currently carries three scenario views:",
        "",
        "- `scenario_nature_first`",
        "- `scenario_balanced`",
        "- `scenario_low_conflict`",
        "",
        "An undersized-cell penalty is applied so clipped coastal or boundary fragments do not dominate the shortlist.",
        "",
        "## Scenario Score Summary",
        "",
    ]

    lines.extend(scenario_block(scores))

    lines.extend(
        [
            "## Published Outputs From This Run",
            "",
            maybe_reference(args.top_candidates_summary_path, "Balanced top-100 shortlist summary"),
            maybe_reference(args.cluster_summary_path, "Balanced candidate-zone summary"),
            maybe_reference(args.validation_summary_path, "Validation summary"),
            maybe_reference(args.app_path, "Standalone shortlist explorer"),
            "",
            "## Main Limitations",
            "",
            "- Opportunity scores should not be read as proof of ecological outcomes.",
            "- Agricultural opportunity remains a simplified tradeoff proxy rather than a full delivery-feasibility model.",
            "- Flood and peat behavior depends on the active source data recorded in the run.",
            "- Observation-based biodiversity signals remain effort-sensitive and incomplete.",
            "- High-ranking cells should be treated as candidate areas for follow-up, not final recommendations.",
            "",
        ]
    )

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    args.out_path.write_text("\n".join(lines) + "\n")
    print(args.out_path)


if __name__ == "__main__":
    main()
