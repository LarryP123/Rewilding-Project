from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Group top-ranked cells into spatial candidate zones and summarize them.",
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km_v4/hex_scores.parquet"),
        help="Path to the scored cell layer.",
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
        help="Number of top cells to cluster.",
    )
    parser.add_argument(
        "--cluster-distance-m",
        type=float,
        default=20_000,
        help="Distance threshold used to merge nearby candidate cells into zones.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outouts/candidate_clusters"),
        help="Directory for summary outputs.",
    )
    return parser.parse_args()


def build_clusters(top: gpd.GeoDataFrame, cluster_distance_m: float) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    centroids = top[["hex_id", "geometry"]].copy()
    centroids["geometry"] = centroids.geometry.centroid

    buffered = centroids.copy()
    buffered["geometry"] = buffered.geometry.buffer(cluster_distance_m)
    merged = buffered.union_all()

    if merged.geom_type == "Polygon":
        geoms = [merged]
    else:
        geoms = list(merged.geoms)

    clusters = gpd.GeoDataFrame(
        {"cluster_id": [f"cluster_{i:02d}" for i in range(1, len(geoms) + 1)]},
        geometry=geoms,
        crs=top.crs,
    )

    assigned = gpd.sjoin(
        centroids,
        clusters,
        how="left",
        predicate="within",
    ).drop(columns=["index_right"])

    top_with_clusters = top.merge(assigned[["hex_id", "cluster_id"]], on="hex_id", how="left")
    return clusters, top_with_clusters


def cluster_summary(top_with_clusters: gpd.GeoDataFrame, scenario: str) -> pd.DataFrame:
    working = top_with_clusters.copy()
    centroids = working.geometry.centroid
    working["centroid_easting_m"] = centroids.x.round(0)
    working["centroid_northing_m"] = centroids.y.round(0)

    summary = (
        working.groupby("cluster_id", as_index=False)
        .agg(
            cell_count=("hex_id", "count"),
            scenario_score_mean=(scenario, "mean"),
            scenario_score_max=(scenario, "max"),
            habitat_share_mean=("priority_habitat_share", "mean"),
            connectivity_mean=("connectivity_score", "mean"),
            restoration_mean=("restoration_opportunity_score", "mean"),
            agri_mean=("agri_opportunity_score_raw", "mean"),
            centroid_easting_m=("centroid_easting_m", "mean"),
            centroid_northing_m=("centroid_northing_m", "mean"),
        )
        .sort_values(["scenario_score_max", "cell_count"], ascending=[False, False])
        .reset_index(drop=True)
    )
    summary["cluster_rank"] = range(1, len(summary) + 1)
    return summary[
        [
            "cluster_rank",
            "cluster_id",
            "cell_count",
            "scenario_score_max",
            "scenario_score_mean",
            "habitat_share_mean",
            "connectivity_mean",
            "restoration_mean",
            "agri_mean",
            "centroid_easting_m",
            "centroid_northing_m",
        ]
    ]


def top_cells_text(top_with_clusters: gpd.GeoDataFrame, scenario: str, cluster_id: str, limit: int = 5) -> str:
    subset = (
        top_with_clusters[top_with_clusters["cluster_id"] == cluster_id]
        .sort_values(scenario, ascending=False)
        .head(limit)
    )
    return subset[
        [
            "hex_id",
            scenario,
            "priority_habitat_share",
            "connectivity_score",
            "restoration_opportunity_score",
        ]
    ].round(2).to_string(index=False)


def main() -> None:
    args = parse_args()
    scores = gpd.read_parquet(args.scores_path)
    top = scores.sort_values(args.scenario, ascending=False).head(args.top_n).copy()
    clusters, top_with_clusters = build_clusters(top, args.cluster_distance_m)

    summary = cluster_summary(top_with_clusters, args.scenario)
    cluster_shapes = (
        top_with_clusters.dissolve(by="cluster_id", as_index=False)[["cluster_id", "geometry"]]
        .merge(summary[["cluster_id", "cluster_rank", "cell_count", "scenario_score_max", "scenario_score_mean"]], on="cluster_id", how="left")
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.scenario}_top_{args.top_n}_clusters"

    csv_path = args.out_dir / f"{stem}.csv"
    summary_path = args.out_dir / f"{stem}_summary.md"
    geojson_path = args.out_dir / f"{stem}.geojson"

    summary.round(2).to_csv(csv_path, index=False)
    cluster_shapes.to_file(geojson_path, driver="GeoJSON")

    lines = [
        f"# Candidate Zones: {args.scenario}",
        "",
        f"Source layer: `{args.scores_path}`",
        f"Top cells clustered: {args.top_n}",
        f"Cluster distance: {int(args.cluster_distance_m)} m",
        "",
        "## Zone summary",
        "",
        summary.round(2).to_string(index=False),
        "",
        "## Top cells per zone",
        "",
    ]

    for row in summary.itertuples(index=False):
        lines.append(f"### {row.cluster_id} (rank {row.cluster_rank}, {row.cell_count} cells)")
        lines.append("")
        lines.append(top_cells_text(top_with_clusters, args.scenario, row.cluster_id))
        lines.append("")

    summary_path.write_text("\n".join(lines) + "\n")

    print(f"csv: {csv_path}")
    print(f"geojson: {geojson_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
