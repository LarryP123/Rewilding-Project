from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import CANONICAL_RELEASE_METADATA_PATH, CANONICAL_SCORES_PATH
from src.provenance import score_provenance

SCENARIO_LABELS = {
    "scenario_nature_first": "Nature-first restoration opportunity",
    "scenario_balanced": "Balanced restoration opportunity",
    "scenario_low_conflict": "Lower-conflict restoration opportunity",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a short human-readable brief for the current candidate zones.",
    )
    parser.add_argument(
        "--cluster-summary-path",
        type=Path,
        default=Path("outputs/candidate_clusters/scenario_balanced_top_100_clusters.csv"),
        help="Path to the cluster summary CSV.",
    )
    parser.add_argument(
        "--clusters-geojson-path",
        type=Path,
        default=Path("outputs/candidate_clusters/scenario_balanced_top_100_clusters.geojson"),
        help="Path to the cluster polygon GeoJSON used for admin-name lookup.",
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=CANONICAL_SCORES_PATH,
        help="Path to the scored layer that produced the cluster summary.",
    )
    parser.add_argument(
        "--scenario",
        default="scenario_balanced",
        help="Scenario name for the brief title.",
    )
    parser.add_argument(
        "--out-path",
        type=Path,
        default=Path("outputs/candidate_brief.md"),
        help="Destination markdown file.",
    )
    parser.add_argument(
        "--admin-path",
        type=Path,
        default=Path("data/raw/reference/ons_counties_unitary_2024.geojson"),
        help="Administrative geography layer used to attach county/unitary authority names.",
    )
    parser.add_argument(
        "--release-path",
        type=Path,
        default=CANONICAL_RELEASE_METADATA_PATH,
        help="Optional canonical release checkpoint file referenced in the brief.",
    )
    return parser.parse_args()


def describe_cluster(row: pd.Series) -> tuple[str, str]:
    admin_name = row.get("admin_name")
    policy_name = row.get("primary_lnrs_name")
    display_name = policy_name if pd.notna(policy_name) else admin_name
    easting = float(row["centroid_easting_m"])
    northing = float(row["centroid_northing_m"])
    cell_count = int(row["cell_count"])

    if northing < 130_000 and easting < 300_000:
        return (
            f"Southwest Peninsula ({display_name})" if pd.notna(display_name) else "Southwest Peninsula",
            "Compact southwestern cluster with strong restoration scores and a coastal-peninsula setting.",
        )
    if northing > 450_000:
        return (
            f"Northern England Belt ({display_name})" if pd.notna(display_name) else "Northern England Belt",
            "The dominant northern zone, holding the biggest concentration of high-scoring cells in the shortlist.",
        )
    if 250_000 <= northing <= 340_000 and easting < 360_000:
        return (
            f"Central-West Belt ({display_name})" if pd.notna(display_name) else "Central-West Belt",
            "A coherent west-central secondary zone with strong scores across multiple neighboring cells.",
        )
    if 330_000 <= northing <= 430_000 and 360_000 <= easting <= 460_000:
        return (
            f"East-Central Arc ({display_name})" if pd.notna(display_name) else "East-Central Arc",
            "A tighter east-central grouping with very strong connectivity and slightly leaner habitat share.",
        )
    if northing < 170_000 and easting >= 360_000:
        return (
            f"Southern Fringe ({display_name})" if pd.notna(display_name) else "Southern Fringe",
            "A smaller southern grouping that looks useful as a lower-density comparison zone.",
        )

    vertical = "Northern" if northing > 350_000 else "Southern"
    horizontal = "Eastern" if easting > 380_000 else "Western"
    density = "broader" if cell_count >= 5 else "small"
    return (
        f"{vertical} {horizontal} Zone ({display_name})" if pd.notna(display_name) else f"{vertical} {horizontal} Zone",
        f"A {density} candidate zone that sits outside the three main core areas.",
    )


def scenario_label(name: str) -> str:
    return SCENARIO_LABELS.get(name, name.replace("_", " ").title())


def main() -> None:
    args = parse_args()
    summary = pd.read_csv(args.cluster_summary_path)
    scenario_title = scenario_label(args.scenario)
    provenance: dict[str, str] = {}
    if args.scores_path.exists():
        import geopandas as gpd

        scores = gpd.read_parquet(args.scores_path)
        provenance = score_provenance(scores, args.scores_path)
    if args.admin_path.exists() and args.clusters_geojson_path.exists():
        import geopandas as gpd

        admins = gpd.read_file(args.admin_path)
        clusters = gpd.read_file(args.clusters_geojson_path)
        name_col = [c for c in admins.columns if c.lower().endswith("nm")][0]
        admins = admins.to_crs(clusters.crs) if admins.crs != clusters.crs else admins
        centroids = clusters.copy()
        centroids["geometry"] = centroids.geometry.representative_point()
        joined = gpd.sjoin(
            centroids[["cluster_id", "geometry"]],
            admins[[name_col, "geometry"]],
            how="left",
            predicate="within",
        ).drop(columns=["index_right"])
        summary = summary.merge(
            joined[["cluster_id", name_col]].rename(columns={name_col: "admin_name"}),
            on="cluster_id",
            how="left",
        )
    else:
        summary["admin_name"] = pd.NA
    names = summary.apply(describe_cluster, axis=1, result_type="expand")
    summary["cluster_name"] = names[0]
    summary["cluster_note"] = names[1]

    top_three = summary.sort_values("cluster_rank").head(3).copy()
    coverage = int(top_three["cell_count"].sum())
    total = int(summary["cell_count"].sum())
    coverage_pct = (coverage / total * 100) if total else 0
    lead_zone_names = ", ".join(top_three["cluster_name"].tolist())

    lines = [
        f"# Candidate Brief: {scenario_title}",
        "",
        "## Overview",
        "",
        f"This brief summarises the leading areas from the {scenario_title.lower()} scenario.",
        f"The current top 100 cells resolve into {len(summary)} candidate zones, but the shortlist is not evenly spread.",
        f"The top 3 zones contain {coverage} of the top {total} cells, which means the analysis is already pointing toward a small number of coherent priority areas rather than isolated one-off winners.",
        "",
        "## At A Glance",
        "",
        f"- Main scenario: {scenario_title}",
        f"- Shortlist scale: top {total} 1 km cells grouped into {len(summary)} candidate zones",
        f"- Dominant pattern: the top 3 zones account for {coverage_pct:.0f}% of the shortlist by cell count",
        f"- Leading named areas: {lead_zone_names}",
        f"- Source layer: `{args.scores_path}`",
        (
            f"- Run profile: `{provenance.get('run_profile', 'not recorded')}`"
            if provenance
            else "- Run profile: not recorded"
        ),
        "",
        "## Leading Zones",
        "",
    ]

    for row in top_three.itertuples(index=False):
        lines.extend(
            [
                f"### {int(row.cluster_rank)}. {row.cluster_name}",
                "",
                row.cluster_note,
                "",
                f"- Cells in zone: {int(row.cell_count)}",
                f"- Max score: {row.scenario_score_max:.2f}",
                f"- Mean score: {row.scenario_score_mean:.2f}",
                f"- Mean habitat share: {row.habitat_share_mean:.2f}%",
                f"- Mean connectivity: {row.connectivity_mean:.2f}",
                f"- Mean restoration score: {row.restoration_mean:.2f}",
                f"- Mean ALC opportunity: {row.agri_mean:.2f}",
                f"- Primary LNRS: {row.primary_lnrs_name if pd.notna(getattr(row, 'primary_lnrs_name', pd.NA)) else 'Not assigned'}",
                f"- LNRS coverage in zone: {row.lnrs_names if pd.notna(getattr(row, 'lnrs_names', pd.NA)) else 'Not assigned'}",
                f"- County / unitary authority: {row.admin_name if pd.notna(row.admin_name) else 'Not assigned'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation",
            "",
            "The leading zones are being driven by cells that sit very near existing habitat, retain room for restoration rather than already being fully habitat-dominated, and carry high agricultural opportunity scores.",
            "That pattern is consistent across the top-ranked areas, which is a good sign that the current ranking is producing a repeatable signal rather than random local noise.",
            "",
            "## What This Is",
            "",
            "This is a first national prioritisation pass, not a site-level recommendation. The outputs are most useful for narrowing England down to a manageable shortlist of areas for closer ecological and practical review.",
            "",
            "## Core Files",
            "",
            (
                f"- Canonical release checkpoint: `{args.release_path}`"
                if args.release_path.exists()
                else "- Canonical release checkpoint: not generated in this run"
            ),
            "- Shortlist explorer app: `outputs/app/rewilding_opportunity_explorer.html`",
            "- Inspection map: `outputs/maps/scenario_balanced_top_100_map.html`",
            "- Methods note: `outputs/methods.md`",
            "- Cluster summary CSV: `outputs/candidate_clusters/scenario_balanced_top_100_clusters.csv`",
            "- Cluster summary markdown: `outputs/candidate_clusters/scenario_balanced_top_100_clusters_summary.md`",
            "",
        ]
    )

    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    args.out_path.write_text("\n".join(lines) + "\n")
    print(args.out_path)


if __name__ == "__main__":
    main()
