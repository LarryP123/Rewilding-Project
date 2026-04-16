from __future__ import annotations

import argparse
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.score import SCENARIO_WEIGHTS, apply_scenarios


NEW_OBJECTIVE_COLUMNS = [
    "flood_opportunity_score_raw",
    "peat_opportunity_score_raw",
    "bird_observation_score_raw",
]

CASE_STUDY_COLUMNS = [
    "priority_habitat_share",
    "connectivity_score",
    "restoration_opportunity_score",
    "agri_opportunity_score_raw",
    "flood_opportunity_score_raw",
    "peat_opportunity_score_raw",
    "bird_observation_score_raw",
    "habitat_mosaic_score",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate scenario stability and sensitivity for the enriched model.",
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km_v4/hex_scores.parquet"),
        help="Path to the canonical scored hex layer.",
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km_v4/hex_scores_pre_meaningful_scores.parquet"),
        help="Optional pre-enrichment comparison layer.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="Shortlist size used for stability and case-study analysis.",
    )
    parser.add_argument(
        "--weight-perturbation",
        type=float,
        default=0.2,
        help="Relative weight perturbation used in sensitivity tests.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/validation"),
        help="Directory for validation outputs.",
    )
    parser.add_argument(
        "--admin-path",
        type=Path,
        default=Path("data/raw/reference/ons_counties_unitary_2024.geojson"),
        help="Optional admin geography layer used to attach place names.",
    )
    return parser.parse_args()


def shortlist_ids(frame: pd.DataFrame, scenario: str, top_n: int) -> list[str]:
    return frame.sort_values(scenario, ascending=False).head(top_n)["hex_id"].tolist()


def shortlist_overlap(frame: pd.DataFrame, scenario_a: str, scenario_b: str, top_n: int) -> dict[str, object]:
    ids_a = set(shortlist_ids(frame, scenario_a, top_n))
    ids_b = set(shortlist_ids(frame, scenario_b, top_n))
    intersection = ids_a & ids_b
    union = ids_a | ids_b
    return {
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
        "top_n": top_n,
        "shared_cells": len(intersection),
        "jaccard_overlap": round(len(intersection) / len(union), 3) if union else 0.0,
    }


def build_rank_frame(frame: pd.DataFrame, scenarios: list[str]) -> pd.DataFrame:
    rank_frame = frame[["hex_id"]].copy()
    for scenario in scenarios:
        rank_frame[f"{scenario}_rank"] = frame[scenario].rank(method="min", ascending=False)
    return rank_frame


def scenario_stability(scores: gpd.GeoDataFrame, scenarios: list[str], top_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    pairwise = []
    for index, scenario_a in enumerate(scenarios):
        for scenario_b in scenarios[index + 1 :]:
            pairwise.append(shortlist_overlap(scores, scenario_a, scenario_b, top_n))

    rank_frame = build_rank_frame(scores, scenarios)
    top_sets = {scenario: set(shortlist_ids(scores, scenario, top_n)) for scenario in scenarios}
    stable_ids = set.intersection(*top_sets.values())
    stable = rank_frame[rank_frame["hex_id"].isin(stable_ids)].copy()
    if stable.empty:
        stable["mean_rank"] = pd.Series(dtype="float64")
    else:
        stable["mean_rank"] = stable[[f"{scenario}_rank" for scenario in scenarios]].mean(axis=1)
        stable = stable.sort_values("mean_rank")
    return pd.DataFrame(pairwise), stable


def baseline_comparison(
    scores: gpd.GeoDataFrame,
    baseline: gpd.GeoDataFrame | None,
    scenarios: list[str],
    top_n: int,
) -> pd.DataFrame:
    if baseline is None:
        return pd.DataFrame()

    rows = []
    for scenario in scenarios:
        current_ids = set(shortlist_ids(scores, scenario, top_n))
        baseline_ids = set(shortlist_ids(baseline, scenario, top_n))
        shared = current_ids & baseline_ids
        rows.append(
            {
                "scenario": scenario,
                "top_n": top_n,
                "shared_cells": len(shared),
                "replaced_cells": top_n - len(shared),
                "shared_pct": round(len(shared) / top_n * 100, 1),
            }
        )
    return pd.DataFrame(rows)


def perturb_weights(
    weights: dict[str, float],
    target_column: str,
    direction: str,
    amount: float,
) -> dict[str, float]:
    factor = 1 + amount if direction == "up" else 1 - amount
    updated = dict(weights)
    updated[target_column] = updated[target_column] * factor
    total = sum(updated.values())
    return {column: value / total for column, value in updated.items()}


def sensitivity_analysis(
    scores: gpd.GeoDataFrame,
    scenarios: list[str],
    top_n: int,
    amount: float,
) -> pd.DataFrame:
    rows = []
    for scenario in scenarios:
        original_top = set(shortlist_ids(scores, scenario, top_n))
        original_weights = SCENARIO_WEIGHTS[scenario]
        required_columns = [column for column in original_weights if column in NEW_OBJECTIVE_COLUMNS]
        if any(column not in scores.columns for column in required_columns):
            continue
        available_targets = [
            column
            for column in NEW_OBJECTIVE_COLUMNS
            if column in original_weights and column in scores.columns
        ]
        for target in available_targets:
            for direction in ["down", "up"]:
                perturbed_weights = {scenario: perturb_weights(original_weights, target, direction, amount)}
                rescored = apply_scenarios(scores.copy(), scenario_weights=perturbed_weights)
                new_top = set(shortlist_ids(rescored, scenario, top_n))
                shared = len(original_top & new_top)
                rows.append(
                    {
                        "scenario": scenario,
                        "target_column": target,
                        "direction": direction,
                        "weight_change_pct": int(amount * 100),
                        "shared_cells": shared,
                        "replaced_cells": top_n - shared,
                        "shared_pct": round(shared / top_n * 100, 1),
                    }
                )
    return pd.DataFrame(rows)


def add_admin_names(frame: gpd.GeoDataFrame, admin_path: Path) -> gpd.GeoDataFrame:
    if not admin_path.exists():
        frame["admin_name"] = pd.NA
        return frame

    admins = gpd.read_file(admin_path)
    name_candidates = [column for column in admins.columns if column.lower().endswith("nm")]
    if not name_candidates:
        frame["admin_name"] = pd.NA
        return frame

    name_column = name_candidates[0]
    working = frame.copy()
    working["geometry"] = working.geometry.representative_point()
    admins = admins.to_crs(working.crs) if admins.crs != working.crs else admins
    joined = gpd.sjoin(
        working[["hex_id", "geometry"]],
        admins[[name_column, "geometry"]],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"])
    return frame.merge(
        joined[["hex_id", name_column]].rename(columns={name_column: "admin_name"}),
        on="hex_id",
        how="left",
    )


def best_driver_text(row: pd.Series) -> str:
    available = {
        column: float(row[column])
        for column in CASE_STUDY_COLUMNS
        if column in row.index and pd.notna(row[column])
    }
    ranked = sorted(available.items(), key=lambda item: item[1], reverse=True)[:3]
    labels = {
        "priority_habitat_share": "habitat share",
        "connectivity_score": "connectivity",
        "restoration_opportunity_score": "restoration opportunity",
        "agri_opportunity_score_raw": "lower agricultural conflict",
        "flood_opportunity_score_raw": "flood opportunity",
        "peat_opportunity_score_raw": "peat opportunity",
        "bird_observation_score_raw": "bird observation score",
        "habitat_mosaic_score": "habitat mosaic",
    }
    return ", ".join(f"{labels.get(column, column)} {value:.1f}" for column, value in ranked)


def build_case_studies(
    scores: gpd.GeoDataFrame,
    stable: pd.DataFrame,
    scenarios: list[str],
    top_n: int,
    admin_path: Path,
) -> pd.DataFrame:
    rank_frame = build_rank_frame(scores, scenarios)
    enriched = scores.merge(rank_frame, on="hex_id", how="left")
    enriched = add_admin_names(enriched, admin_path)

    case_rows = []

    if not stable.empty:
        stable_hex_id = stable.iloc[0]["hex_id"]
        stable_row = enriched.loc[enriched["hex_id"] == stable_hex_id].iloc[0]
        case_rows.append(
            {
                "case_type": "stable_across_objectives",
                "hex_id": stable_hex_id,
                "admin_name": stable_row.get("admin_name"),
                "headline": "Consistently strong under all three objectives",
                "detail": f"Ranks {int(stable_row['scenario_nature_first_rank'])}, {int(stable_row['scenario_balanced_rank'])}, and {int(stable_row['scenario_low_conflict_rank'])} across the three scenarios; strongest signals are {best_driver_text(stable_row)}.",
            }
        )

    balanced_top = set(shortlist_ids(scores, "scenario_balanced", top_n))
    nature_first = enriched.sort_values(
        ["scenario_nature_first_rank", "scenario_balanced_rank"],
        ascending=[True, False],
    )
    nature_first = nature_first.loc[~nature_first["hex_id"].isin(balanced_top)].copy()
    if not nature_first.empty:
        row = nature_first.iloc[0]
        case_rows.append(
            {
                "case_type": "nature_first_specialist",
                "hex_id": row["hex_id"],
                "admin_name": row.get("admin_name"),
                "headline": "Moves up when peat, flood, and biodiversity matter more",
                "detail": f"Nature-first rank {int(row['scenario_nature_first_rank'])} versus balanced rank {int(row['scenario_balanced_rank'])}; strongest signals are {best_driver_text(row)}.",
            }
        )

    low_conflict = enriched.sort_values(
        ["scenario_low_conflict_rank", "scenario_balanced_rank"],
        ascending=[True, False],
    )
    low_conflict = low_conflict.loc[~low_conflict["hex_id"].isin(balanced_top)].copy()
    if not low_conflict.empty:
        row = low_conflict.iloc[0]
        case_rows.append(
            {
                "case_type": "low_conflict_specialist",
                "hex_id": row["hex_id"],
                "admin_name": row.get("admin_name"),
                "headline": "Useful where delivery feasibility matters most",
                "detail": f"Low-conflict rank {int(row['scenario_low_conflict_rank'])} versus balanced rank {int(row['scenario_balanced_rank'])}; strongest signals are {best_driver_text(row)}.",
            }
        )

    return pd.DataFrame(case_rows)


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    subset = frame[columns].copy() if columns is not None else frame.copy()
    subset = subset.fillna("")
    headers = [str(column) for column in subset.columns]
    separator = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in subset.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    scores = gpd.read_parquet(args.scores_path)
    baseline = gpd.read_parquet(args.baseline_path) if args.baseline_path.exists() else None
    scenarios = [scenario for scenario in SCENARIO_WEIGHTS if scenario in scores.columns]

    pairwise_overlap, stable = scenario_stability(scores, scenarios, args.top_n)
    baseline_shift = baseline_comparison(scores, baseline, scenarios, args.top_n)
    sensitivity = sensitivity_analysis(scores, scenarios, args.top_n, args.weight_perturbation)
    case_studies = build_case_studies(scores, stable, scenarios, args.top_n, args.admin_path)

    pairwise_path = args.out_dir / "scenario_overlap.csv"
    stable_path = args.out_dir / "stable_cells.csv"
    baseline_path = args.out_dir / "baseline_shift.csv"
    sensitivity_path = args.out_dir / "weight_sensitivity.csv"
    case_studies_path = args.out_dir / "case_studies.csv"
    summary_path = args.out_dir / "validation_summary.md"

    pairwise_overlap.to_csv(pairwise_path, index=False)
    stable.to_csv(stable_path, index=False)
    baseline_shift.to_csv(baseline_path, index=False)
    sensitivity.to_csv(sensitivity_path, index=False)
    case_studies.to_csv(case_studies_path, index=False)

    shared_all = len(stable)
    sensitivity_summary = (
        sensitivity.groupby("scenario")["shared_pct"].agg(["min", "mean", "max"]).reset_index()
        if not sensitivity.empty
        else pd.DataFrame()
    )

    lines = [
        "# Enriched Model Validation",
        "",
        f"Source layer: `{args.scores_path}`",
        f"Shortlist size: top {args.top_n} cells",
        "",
        "## Scenario Stability",
        "",
        f"{shared_all} cells appear in the top {args.top_n} under all three scenario objectives.",
        "",
        markdown_table(
            pairwise_overlap,
            ["scenario_a", "scenario_b", "shared_cells", "jaccard_overlap"],
        ),
        "",
        "## Enriched vs Earlier Score Layer",
        "",
        markdown_table(
            baseline_shift,
            ["scenario", "shared_cells", "replaced_cells", "shared_pct"],
        ),
        "",
        "## Weight Sensitivity",
        "",
        "This perturbs the flood, peat, and biodiversity weights up and down while renormalising each scenario to 100%.",
        "",
        markdown_table(sensitivity_summary),
        "",
        "## Short Case Studies",
        "",
    ]

    if case_studies.empty:
        lines.append("_No case studies generated._")
    else:
        for row in case_studies.itertuples(index=False):
            place_name = row.admin_name if pd.notna(row.admin_name) else "Unassigned admin area"
            lines.extend(
                [
                    f"### {row.headline}",
                    "",
                    f"- Hex: `{row.hex_id}`",
                    f"- Area: {place_name}",
                    f"- Why it matters: {row.detail}",
                    "",
                ]
            )

    summary_path.write_text("\n".join(lines) + "\n")

    print(f"summary: {summary_path}")
    print(f"overlap_csv: {pairwise_path}")
    print(f"stable_csv: {stable_path}")
    print(f"baseline_csv: {baseline_path}")
    print(f"sensitivity_csv: {sensitivity_path}")
    print(f"case_studies_csv: {case_studies_path}")


if __name__ == "__main__":
    main()
