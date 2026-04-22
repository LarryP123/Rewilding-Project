from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import CANONICAL_SCORES_PATH

SCENARIO_LABELS = {
    "scenario_nature_first": "Nature-first restoration opportunity",
    "scenario_balanced": "Balanced restoration opportunity",
    "scenario_low_conflict": "Lower-conflict restoration opportunity",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a standalone local inspection map for top-ranked rewilding cells.",
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
        help="Number of top cells to show.",
    )
    parser.add_argument(
        "--out-html",
        type=Path,
        default=Path("outputs/maps/scenario_balanced_top_100_map.html"),
        help="Destination HTML file.",
    )
    parser.add_argument(
        "--clusters-path",
        type=Path,
        default=Path("outputs/candidate_clusters/scenario_balanced_top_100_clusters.geojson"),
        help="Optional cluster polygon layer to overlay.",
    )
    parser.add_argument(
        "--cluster-summary-path",
        type=Path,
        default=Path("outputs/candidate_clusters/scenario_balanced_top_100_clusters.csv"),
        help="Optional cluster summary CSV used for labels.",
    )
    parser.add_argument(
        "--admin-path",
        type=Path,
        default=Path("data/raw/reference/ons_counties_unitary_2024.geojson"),
        help="Administrative geography layer used to attach county/unitary authority names.",
    )
    return parser.parse_args()


def make_projector(
    bounds: tuple[float, float, float, float],
    width: int = 1200,
    padding: int = 28,
) -> tuple[callable, int]:
    minx, miny, maxx, maxy = bounds
    span_x = maxx - minx
    span_y = maxy - miny
    scale = (width - 2 * padding) / span_x if span_x else 1.0
    height = int(span_y * scale + 2 * padding)

    def project(x: float, y: float) -> tuple[float, float]:
        sx = padding + (x - minx) * scale
        sy = height - padding - (y - miny) * scale
        return round(sx, 2), round(sy, 2)

    return project, height


def scale_features(
    gdf: gpd.GeoDataFrame,
    project: callable,
) -> list[dict]:
    features: list[dict] = []
    for row in gdf.itertuples():
        geom = row.geometry
        polygons = []
        if geom.geom_type == "Polygon":
            polygons = [geom]
        elif geom.geom_type == "MultiPolygon":
            polygons = list(geom.geoms)
        else:
            continue

        paths = []
        for polygon in polygons:
            exterior = " ".join(
                f"{x},{y}" for x, y in (project(px, py) for px, py in polygon.exterior.coords)
            )
            holes = [
                " ".join(f"{x},{y}" for x, y in (project(px, py) for px, py in ring.coords))
                for ring in polygon.interiors
            ]
            paths.append({"exterior": exterior, "holes": holes})

        representative = geom.representative_point()
        cx, cy = project(representative.x, representative.y)
        features.append(
            {
                "hex_id": row.hex_id,
                "scenario_score": round(float(getattr(row, "scenario_balanced")), 2)
                if hasattr(row, "scenario_balanced")
                else None,
                "paths": paths,
                "cx": cx,
                "cy": cy,
            }
        )

    return features


def geometry_markup(
    gdf: gpd.GeoDataFrame,
    project: callable,
    *,
    fill: str,
    stroke: str,
    stroke_width: float,
    fill_opacity: float,
    css_class: str,
) -> list[str]:
    markup: list[str] = []
    for geom in gdf.geometry:
        if geom.geom_type == "Polygon":
            polygons = [geom]
        elif geom.geom_type == "MultiPolygon":
            polygons = list(geom.geoms)
        else:
            continue
        for polygon in polygons:
            exterior = " ".join(
                f"{x},{y}" for x, y in (project(px, py) for px, py in polygon.exterior.coords)
            )
            markup.append(
                f"""
                <polygon
                    class="{css_class}"
                    points="{exterior}"
                    fill="{fill}"
                    stroke="{stroke}"
                    stroke-width="{stroke_width}"
                    fill-opacity="{fill_opacity}"
                ></polygon>
                """
            )
    return markup


def cluster_markup(
    clusters: gpd.GeoDataFrame,
    project: callable,
) -> tuple[list[str], list[str]]:
    polygons: list[str] = []
    labels: list[str] = []

    for row in clusters.itertuples():
        geom = row.geometry
        if geom.geom_type == "Polygon":
            parts = [geom]
        elif geom.geom_type == "MultiPolygon":
            parts = list(geom.geoms)
        else:
            continue

        for polygon in parts:
            exterior = " ".join(
                f"{x},{y}" for x, y in (project(px, py) for px, py in polygon.exterior.coords)
            )
            polygons.append(
                f"""
                <polygon
                    class="cluster-zone"
                    points="{exterior}"
                    fill="none"
                    stroke="#234b6b"
                    stroke-width="3"
                    stroke-opacity="0.75"
                    stroke-dasharray="10 8"
                >
                    <title>{html.escape(str(getattr(row, "cluster_name", f"Zone {int(row.cluster_rank)}")))}</title>
                </polygon>
                """
            )

        if "centroid_easting_m" in clusters.columns and "centroid_northing_m" in clusters.columns:
            lx, ly = project(float(row.centroid_easting_m), float(row.centroid_northing_m))
            rank_text = html.escape(str(int(row.cluster_rank)))
            admin_text = html.escape(str(getattr(row, "admin_name", ""))) if getattr(row, "admin_name", None) else ""
            label_title = html.escape(str(getattr(row, "cluster_name", f"Zone {int(row.cluster_rank)}")))
            labels.append(
                f"""
                <g class="cluster-label">
                  <title>{label_title}</title>
                  <circle cx="{lx}" cy="{ly}" r="14" fill="#234b6b" fill-opacity="0.92"></circle>
                  <text x="{lx}" y="{ly + 5}" text-anchor="middle">{rank_text}</text>
                  <text class="cluster-admin-text" x="{lx + 20}" y="{ly + 5}" text-anchor="start">{admin_text}</text>
                </g>
                """
            )

    return polygons, labels


def color_for(value: float, min_value: float, max_value: float) -> str:
    if max_value <= min_value:
        ratio = 0.5
    else:
        ratio = (value - min_value) / (max_value - min_value)
    ratio = max(0.0, min(1.0, ratio))

    stops = [
        (241, 239, 232),
        (217, 194, 122),
        (126, 160, 77),
        (47, 107, 59),
    ]

    scaled = ratio * (len(stops) - 1)
    idx = int(scaled)
    if idx >= len(stops) - 1:
        rgb = stops[-1]
    else:
        local = scaled - idx
        start = stops[idx]
        end = stops[idx + 1]
        rgb = tuple(int(start[i] + (end[i] - start[i]) * local) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def scenario_label(name: str) -> str:
    return SCENARIO_LABELS.get(name, name.replace("_", " ").title())


def describe_cluster(row: pd.Series) -> tuple[str, str]:
    admin_name = row.get("admin_name")
    policy_name = row.get("primary_lnrs_name")
    display_name = policy_name if pd.notna(policy_name) else admin_name
    easting = float(row["centroid_easting_m"])
    northing = float(row["centroid_northing_m"])
    cell_count = int(row["cell_count"])

    if northing < 130_000 and easting < 300_000:
        name = f"Southwest Peninsula ({display_name})" if pd.notna(display_name) else "Southwest Peninsula"
        note = "Compact southwestern cluster with strong restoration scores and a coastal-peninsula setting."
    elif northing > 450_000:
        name = f"Northern England Belt ({display_name})" if pd.notna(display_name) else "Northern England Belt"
        note = "The dominant northern zone, with the biggest concentration of high-scoring cells in the shortlist."
    elif 250_000 <= northing <= 340_000 and easting < 360_000:
        name = f"Central-West Belt ({display_name})" if pd.notna(display_name) else "Central-West Belt"
        note = "A mid-ranking west-central zone that looks like a coherent secondary candidate area."
    elif 330_000 <= northing <= 430_000 and 360_000 <= easting <= 460_000:
        name = f"East-Central Arc ({display_name})" if pd.notna(display_name) else "East-Central Arc"
        note = "A tighter east-central cluster with strong connectivity and slightly leaner habitat share."
    elif northing < 170_000 and easting >= 360_000:
        name = f"Southern Fringe ({display_name})" if pd.notna(display_name) else "Southern Fringe"
        note = "A smaller southern grouping of candidates, useful as a lower-density comparison zone."
    else:
        vertical = "Northern" if northing > 350_000 else "Southern"
        horizontal = "Eastern" if easting > 380_000 else "Western"
        name = (
            f"{vertical} {horizontal} Zone ({display_name})"
            if pd.notna(display_name)
            else f"{vertical} {horizontal} Zone"
        )
        density = "broad" if cell_count >= 5 else "small"
        note = f"A {density} candidate zone that sits outside the main core clusters."

    return name, note


def attach_admin_names(
    summary: pd.DataFrame,
    clusters: gpd.GeoDataFrame,
    admin_path: Path,
) -> pd.DataFrame:
    if not admin_path.exists():
        summary["admin_name"] = pd.NA
        return summary

    admins = gpd.read_file(admin_path)
    name_col = [column for column in admins.columns if column.lower().endswith("nm")][0]
    admins = admins.to_crs(clusters.crs) if admins.crs != clusters.crs else admins
    centroids = clusters[["cluster_id", "geometry"]].copy()
    centroids["geometry"] = centroids.geometry.representative_point()
    joined = gpd.sjoin(
        centroids,
        admins[[name_col, "geometry"]],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"])
    return summary.merge(
        joined[["cluster_id", name_col]].rename(columns={name_col: "admin_name"}),
        on="cluster_id",
        how="left",
    )


def main() -> None:
    args = parse_args()
    scenario_title = scenario_label(args.scenario)
    scores = gpd.read_parquet(args.scores_path)
    boundary = gpd.read_parquet("data/raw/boundaries/england_boundary_analysis.parquet")
    clusters = None
    if args.clusters_path.exists():
        clusters = gpd.read_file(args.clusters_path)
        if args.cluster_summary_path.exists():
            summary = pd.read_csv(args.cluster_summary_path)
            summary = attach_admin_names(summary, clusters, args.admin_path)
            descriptions = summary.apply(describe_cluster, axis=1, result_type="expand")
            summary["cluster_name"] = descriptions[0]
            summary["cluster_note"] = descriptions[1]
            summary["cluster_label_short"] = summary.apply(
                lambda row: (
                    f"{int(row['cluster_rank'])} {row['admin_name']}"
                    if pd.notna(row.get("admin_name"))
                    else str(int(row["cluster_rank"]))
                ),
                axis=1,
            )
            for column in ["cluster_rank", "cell_count", "centroid_easting_m", "centroid_northing_m"]:
                if column in clusters.columns:
                    clusters = clusters.drop(columns=column)
            clusters = clusters.merge(
                summary[
                    [
                        "cluster_id",
                        "cluster_rank",
                        "cell_count",
                        "centroid_easting_m",
                        "centroid_northing_m",
                        "cluster_name",
                        "cluster_note",
                        "admin_name",
                        "cluster_label_short",
                    ]
                ],
                on="cluster_id",
                how="left",
            )
    ranked = scores.sort_values(args.scenario, ascending=False).head(args.top_n).copy()
    ranked = ranked[ranked.geometry.notna() & ~ranked.geometry.is_empty].copy()

    score_min = float(ranked[args.scenario].min())
    score_max = float(ranked[args.scenario].max())

    project, height = make_projector(tuple(boundary.total_bounds))
    features = scale_features(ranked, project)
    boundary_markup = geometry_markup(
        boundary,
        project,
        fill="#dfe6d2",
        stroke="#9aa78f",
        stroke_width=1.5,
        fill_opacity=1.0,
        css_class="england-shape",
    )
    cluster_polygons: list[str] = []
    cluster_labels: list[str] = []
    top_cluster_markup = ""
    summary_badges = ""
    if clusters is not None and not clusters.empty:
        cluster_polygons, cluster_labels = cluster_markup(clusters, project)
        top_clusters = (
            clusters.drop_duplicates("cluster_id")
            .sort_values("cluster_rank")
            .head(3)
        )
        covered_cells = int(top_clusters["cell_count"].sum())
        coverage_pct = round((covered_cells / args.top_n) * 100) if args.top_n else 0
        cluster_cards = []
        for row in top_clusters.itertuples():
            meta_parts = [f"{int(row.cell_count)} cells", f"max score {float(row.scenario_score_max):.2f}"]
            if hasattr(row, "primary_lnrs_name") and pd.notna(row.primary_lnrs_name):
                meta_parts.append(str(row.primary_lnrs_name))
            if hasattr(row, "admin_name") and pd.notna(row.admin_name):
                meta_parts.append(str(row.admin_name))
            cluster_cards.append(
                f"""
                <div class="zone-card">
                  <div class="zone-card-title">{int(row.cluster_rank)}. {html.escape(str(row.cluster_name))}</div>
                  <div class="zone-card-meta">{html.escape(" | ".join(meta_parts))}</div>
                  <div class="zone-card-note">{html.escape(str(row.cluster_note))}</div>
                </div>
                """
            )
        top_cluster_markup = "".join(cluster_cards)
        summary_badges = f"""
        <div class="summary-strip">
          <div class="summary-pill"><span class="summary-pill-label">Scenario</span><strong>{html.escape(scenario_title)}</strong></div>
          <div class="summary-pill"><span class="summary-pill-label">Shortlist</span><strong>Top {args.top_n} cells</strong></div>
          <div class="summary-pill"><span class="summary-pill-label">Lead zones</span><strong>{covered_cells} cells across top 3 zones</strong></div>
          <div class="summary-pill"><span class="summary-pill-label">Coverage</span><strong>{coverage_pct}% of shortlist</strong></div>
        </div>
        """
    property_rows = []
    for row in ranked.itertuples():
        property_rows.append(
            {
                "hex_id": row.hex_id,
                "scenario": round(float(getattr(row, args.scenario)), 2),
                "priority_habitat_share": round(float(row.priority_habitat_share), 2),
                "connectivity_score": round(float(row.connectivity_score), 2),
                "restoration_opportunity_score": round(float(row.restoration_opportunity_score), 2),
                "biodiversity_observation_score_raw": round(float(getattr(row, "biodiversity_observation_score_raw", 0.0)), 2),
                "bird_observation_score_raw": round(float(getattr(row, "bird_observation_score_raw", 0.0)), 2),
                "bird_species_richness": round(float(getattr(row, "bird_species_richness", 0.0)), 2),
                "bird_record_count": round(float(getattr(row, "bird_record_count", 0.0)), 2),
                "mammal_species_richness": round(float(getattr(row, "mammal_species_richness", 0.0)), 2),
                "mammal_record_count": round(float(getattr(row, "mammal_record_count", 0.0)), 2),
                "habitat_mosaic_score": round(float(row.habitat_mosaic_score), 2),
                "agri_opportunity_score_raw": round(float(row.agri_opportunity_score_raw), 2),
                "cell_area_ratio": round(float(row.cell_area_ratio), 3),
                "undersized_cell_penalty": round(float(row.undersized_cell_penalty), 3),
            }
        )

    properties_by_hex = {row["hex_id"]: row for row in property_rows}
    feature_markup: list[str] = []
    for feature in features:
        props = properties_by_hex[feature["hex_id"]]
        fill = color_for(props["scenario"], score_min, score_max)
        outline = "#17351f" if props["undersized_cell_penalty"] < 1 else "#355e3b"
        weight = 2 if props["undersized_cell_penalty"] < 1 else 1
        title = html.escape(
            f"{feature['hex_id']} | score {props['scenario']:.2f} | habitat {props['priority_habitat_share']:.2f}%"
        )
        data_json = html.escape(json.dumps(props))

        for path in feature["paths"]:
            feature_markup.append(
                f"""
                <polygon
                    class="cell"
                    points="{path['exterior']}"
                    fill="{fill}"
                    stroke="{outline}"
                    stroke-width="{weight}"
                    fill-opacity="0.82"
                    data-hex="{feature['hex_id']}"
                    data-props="{data_json}"
                    data-cx="{feature['cx']}"
                    data-cy="{feature['cy']}"
                >
                    <title>{title}</title>
                </polygon>
                """
            )

    legend_steps = []
    for i in range(5):
        value = score_min + ((score_max - score_min) * i / 4 if score_max > score_min else 0)
        legend_steps.append(
            f"""
            <div class="legend-row">
              <span class="swatch" style="background:{color_for(value, score_min, score_max)};"></span>
              <span>{value:.2f}</span>
            </div>
            """
        )

    initial = property_rows[0]
    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>England Rewilding Opportunity Map</title>
  <style>
    :root {{
      --bg: #f4f1e8;
      --panel: #fffdf7;
      --ink: #1f2933;
      --muted: #5a6772;
      --border: #d8d4c8;
      --accent: #355e3b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Helvetica Neue", "Segoe UI", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8f6ef 0%, #efe9db 100%);
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      min-height: 100vh;
    }}
    .main {{
      padding: 18px;
    }}
    .card {{
      background: rgba(255, 253, 247, 0.96);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: 0 10px 30px rgba(31, 41, 51, 0.08);
    }}
    .header {{
      padding: 14px 16px 0 16px;
    }}
    .header h1 {{
      margin: 0 0 4px 0;
      font-size: 20px;
    }}
    .header p {{
      margin: 0 0 12px 0;
      color: var(--muted);
      line-height: 1.4;
    }}
    .summary-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0 0 14px 0;
    }}
    .summary-pill {{
      display: inline-flex;
      flex-direction: column;
      gap: 2px;
      padding: 8px 12px;
      border-radius: 10px;
      background: rgba(53, 94, 59, 0.08);
      border: 1px solid rgba(53, 94, 59, 0.14);
      min-width: 150px;
    }}
    .summary-pill-label {{
      font-size: 11px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .summary-pill strong {{
      font-size: 14px;
      line-height: 1.3;
    }}
    .map-wrap {{
      padding: 0 16px 16px 16px;
      position: relative;
      display: flex;
      flex-direction: column;
    }}
    .map-toolbar {{
      position: absolute;
      top: 10px;
      right: 26px;
      z-index: 3;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .map-toolbar button {{
      border: 1px solid var(--border);
      background: rgba(255, 253, 247, 0.96);
      color: var(--ink);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 13px;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(31, 41, 51, 0.08);
    }}
    .map-toolbar button:hover {{
      background: #ffffff;
    }}
    svg {{
      width: min(100%, calc((100vh - 220px) * 1200 / {height}));
      height: auto;
      display: block;
      margin: 0 auto;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.85), rgba(255,255,255,0.45)),
        #ece6d7;
      border-radius: 12px;
      border: 1px solid var(--border);
      touch-action: none;
    }}
    .cell {{
      cursor: pointer;
      transition: fill-opacity 120ms ease, stroke-width 120ms ease;
      vector-effect: non-scaling-stroke;
    }}
    .england-shape {{
      vector-effect: non-scaling-stroke;
    }}
    .cluster-zone {{
      vector-effect: non-scaling-stroke;
      pointer-events: none;
    }}
    .cluster-label text {{
      fill: white;
      font-size: 14px;
      font-weight: 700;
      font-family: Arial, sans-serif;
      pointer-events: none;
    }}
    .cluster-admin-text {{
      fill: #234b6b !important;
      font-size: 12px !important;
      font-weight: 700;
      paint-order: stroke;
      stroke: rgba(255, 253, 247, 0.95);
      stroke-width: 3px;
      stroke-linejoin: round;
    }}
    .cluster-label circle {{
      pointer-events: none;
    }}
    .cell:hover,
    .cell.active {{
      fill-opacity: 0.98;
      stroke: #111;
      stroke-width: 2.5;
    }}
    .centroid {{
      pointer-events: none;
      fill: rgba(17, 17, 17, 0.28);
    }}
    .hint {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    .sidebar {{
      border-left: 1px solid rgba(216, 212, 200, 0.8);
      background: rgba(255, 253, 247, 0.86);
      padding: 18px;
      backdrop-filter: blur(4px);
    }}
    .sidebar h2 {{
      margin: 0 0 4px 0;
      font-size: 18px;
    }}
    .sidebar p {{
      margin: 0 0 14px 0;
      color: var(--muted);
      line-height: 1.4;
    }}
    .sidebar-kicker {{
      margin: 0 0 6px 0;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .metric {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      padding: 8px 0;
      border-bottom: 1px solid rgba(216, 212, 200, 0.7);
      font-size: 14px;
    }}
    .metric span:last-child {{
      font-weight: 700;
    }}
    .legend {{
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid rgba(216, 212, 200, 0.7);
    }}
    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      font-size: 13px;
      color: var(--muted);
    }}
    .swatch {{
      width: 18px;
      height: 18px;
      border-radius: 4px;
      border: 1px solid rgba(31, 41, 51, 0.15);
      display: inline-block;
    }}
    .footer-note {{
      margin-top: 14px;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
    }}
    .zone-section {{
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid rgba(216, 212, 200, 0.7);
    }}
    .zone-card {{
      margin-top: 10px;
      padding: 10px 12px;
      border: 1px solid rgba(216, 212, 200, 0.9);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.72);
    }}
    .zone-card-title {{
      font-weight: 700;
      font-size: 14px;
      margin-bottom: 4px;
    }}
    .zone-card-meta {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }}
    .zone-card-note {{
      font-size: 13px;
      line-height: 1.4;
    }}
    @media (max-width: 980px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      svg {{
        width: 100%;
      }}
      .sidebar {{
        border-left: 0;
        border-top: 1px solid rgba(216, 212, 200, 0.8);
      }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <div class="main">
      <div class="card">
        <div class="header">
          <h1>England Rewilding Opportunity Map</h1>
          <p>This view shows the top {args.top_n} 1 km cells under the <strong>{html.escape(scenario_title)}</strong> scenario. It is drawn directly in British National Grid so it opens locally and keeps the national shortlist view stable.</p>
          {summary_badges}
        </div>
        <div class="map-wrap">
          <div class="map-toolbar">
            <button type="button" id="zoom-in">Zoom In</button>
            <button type="button" id="zoom-out">Zoom Out</button>
            <button type="button" id="zoom-selected">Zoom To Selected</button>
            <button type="button" id="reset-view">Reset</button>
          </div>
          <svg id="inspection-map" viewBox="0 0 1200 {height}" role="img" aria-label="Top ranked rewilding opportunity cells in England">
            {"".join(boundary_markup)}
            {"".join(cluster_polygons)}
            {"".join(feature_markup)}
            {"".join(cluster_labels)}
          </svg>
          <div class="hint">Use the buttons or mouse wheel to zoom. Drag the map to pan. Clicking a cell updates the side panel so you can inspect why that area ranks highly.</div>
        </div>
      </div>
    </div>
    <aside class="sidebar">
      <div class="sidebar-kicker">Selected shortlisted cell</div>
      <h2 id="hex-id">{initial["hex_id"]}</h2>
      <p>Click any shortlisted cell to inspect the component signals behind its score.</p>
      <div class="metric"><span>{html.escape(scenario_title)} score</span><span id="scenario">{initial["scenario"]:.2f}</span></div>
      <div class="metric"><span>Habitat share (%)</span><span id="habitat">{initial["priority_habitat_share"]:.2f}</span></div>
      <div class="metric"><span>Connectivity</span><span id="connectivity">{initial["connectivity_score"]:.2f}</span></div>
      <div class="metric"><span>Restoration</span><span id="restoration">{initial["restoration_opportunity_score"]:.2f}</span></div>
      <div class="metric"><span>Biodiversity observation score</span><span id="biodiversity-score">{initial["biodiversity_observation_score_raw"]:.2f}</span></div>
      <div class="metric"><span>Bird species richness</span><span id="bird-richness">{initial["bird_species_richness"]:.2f}</span></div>
      <div class="metric"><span>Bird record count</span><span id="bird-records">{initial["bird_record_count"]:.2f}</span></div>
      <div class="metric"><span>Mammal species richness</span><span id="mammal-richness">{initial["mammal_species_richness"]:.2f}</span></div>
      <div class="metric"><span>Mammal record count</span><span id="mammal-records">{initial["mammal_record_count"]:.2f}</span></div>
      <div class="metric"><span>Mosaic</span><span id="mosaic">{initial["habitat_mosaic_score"]:.2f}</span></div>
      <div class="metric"><span>ALC opportunity</span><span id="agri">{initial["agri_opportunity_score_raw"]:.2f}</span></div>
      <div class="metric"><span>Cell area ratio</span><span id="area-ratio">{initial["cell_area_ratio"]:.3f}</span></div>
      <div class="metric"><span>Boundary penalty</span><span id="penalty">{initial["undersized_cell_penalty"]:.3f}</span></div>
      <div class="legend">
        <strong>Score scale</strong>
        {"".join(legend_steps)}
      </div>
      <div class="zone-section">
        <strong>Top Candidate Zones</strong>
        {top_cluster_markup}
      </div>
      <div class="footer-note">
        This is a national screening view. Cells with lower area ratio would be boundary fragments, so the cleaned shortlist favors full-size or near-full-size hexes.
      </div>
    </aside>
  </div>
  <script>
    const cells = document.querySelectorAll('.cell');
    const svg = document.getElementById('inspection-map');
    const fullView = {{ x: 0, y: 0, width: 1200, height: {height} }};
    let view = {{ ...fullView }};
    let activeCell = null;
    let dragStart = null;

    function renderViewBox() {{
      svg.setAttribute('viewBox', `${{view.x}} ${{view.y}} ${{view.width}} ${{view.height}}`);
    }}

    function clamp(value, min, max) {{
      return Math.max(min, Math.min(max, value));
    }}

    function clampView() {{
      const maxX = fullView.x + fullView.width - view.width;
      const maxY = fullView.y + fullView.height - view.height;
      view.x = clamp(view.x, fullView.x, maxX);
      view.y = clamp(view.y, fullView.y, maxY);
    }}

    function zoomAt(factor, centerX, centerY) {{
      const nextWidth = clamp(view.width / factor, fullView.width / 40, fullView.width);
      const nextHeight = clamp(view.height / factor, fullView.height / 40, fullView.height);
      const relX = (centerX - view.x) / view.width;
      const relY = (centerY - view.y) / view.height;
      view.x = centerX - nextWidth * relX;
      view.y = centerY - nextHeight * relY;
      view.width = nextWidth;
      view.height = nextHeight;
      clampView();
      renderViewBox();
    }}

    function zoomToCell(cell, factor = 18) {{
      const cx = parseFloat(cell.dataset.cx);
      const cy = parseFloat(cell.dataset.cy);
      view.width = clamp(fullView.width / factor, fullView.width / 40, fullView.width);
      view.height = clamp(fullView.height / factor, fullView.height / 40, fullView.height);
      view.x = cx - view.width / 2;
      view.y = cy - view.height / 2;
      clampView();
      renderViewBox();
    }}

    function setActive(cell) {{
      cells.forEach((item) => item.classList.remove('active'));
      cell.classList.add('active');
      activeCell = cell;
      const props = JSON.parse(cell.dataset.props);
      document.getElementById('hex-id').textContent = props.hex_id;
      document.getElementById('scenario').textContent = props.scenario.toFixed(2);
      document.getElementById('habitat').textContent = props.priority_habitat_share.toFixed(2);
      document.getElementById('connectivity').textContent = props.connectivity_score.toFixed(2);
      document.getElementById('restoration').textContent = props.restoration_opportunity_score.toFixed(2);
      document.getElementById('biodiversity-score').textContent = props.biodiversity_observation_score_raw.toFixed(2);
      document.getElementById('bird-richness').textContent = props.bird_species_richness.toFixed(2);
      document.getElementById('bird-records').textContent = props.bird_record_count.toFixed(2);
      document.getElementById('mammal-richness').textContent = props.mammal_species_richness.toFixed(2);
      document.getElementById('mammal-records').textContent = props.mammal_record_count.toFixed(2);
      document.getElementById('mosaic').textContent = props.habitat_mosaic_score.toFixed(2);
      document.getElementById('agri').textContent = props.agri_opportunity_score_raw.toFixed(2);
      document.getElementById('area-ratio').textContent = props.cell_area_ratio.toFixed(3);
      document.getElementById('penalty').textContent = props.undersized_cell_penalty.toFixed(3);
    }}
    cells.forEach((cell, index) => {{
      cell.addEventListener('click', () => {{
        setActive(cell);
        zoomToCell(cell);
      }});
      if (index === 0) {{
        setActive(cell);
      }}
    }});

    svg.addEventListener('wheel', (event) => {{
      event.preventDefault();
      const point = svg.createSVGPoint();
      point.x = event.clientX;
      point.y = event.clientY;
      const cursor = point.matrixTransform(svg.getScreenCTM().inverse());
      zoomAt(event.deltaY < 0 ? 1.35 : 1 / 1.35, cursor.x, cursor.y);
    }}, {{ passive: false }});

    svg.addEventListener('pointerdown', (event) => {{
      dragStart = {{
        x: event.clientX,
        y: event.clientY,
        vx: view.x,
        vy: view.y,
      }};
      svg.setPointerCapture(event.pointerId);
    }});

    svg.addEventListener('pointermove', (event) => {{
      if (!dragStart) return;
      const dx = (event.clientX - dragStart.x) * (view.width / svg.clientWidth);
      const dy = (event.clientY - dragStart.y) * (view.height / svg.clientHeight);
      view.x = dragStart.vx - dx;
      view.y = dragStart.vy - dy;
      clampView();
      renderViewBox();
    }});

    function endDrag() {{
      dragStart = null;
    }}

    svg.addEventListener('pointerup', endDrag);
    svg.addEventListener('pointerleave', endDrag);

    document.getElementById('zoom-in').addEventListener('click', () => zoomAt(1.35, view.x + view.width / 2, view.y + view.height / 2));
    document.getElementById('zoom-out').addEventListener('click', () => zoomAt(1 / 1.35, view.x + view.width / 2, view.y + view.height / 2));
    document.getElementById('zoom-selected').addEventListener('click', () => {{
      if (activeCell) zoomToCell(activeCell);
    }});
    document.getElementById('reset-view').addEventListener('click', () => {{
      view = {{ ...fullView }};
      renderViewBox();
    }});

  </script>
</body>
</html>
"""

    args.out_html.parent.mkdir(parents=True, exist_ok=True)
    args.out_html.write_text(html_out)
    print(args.out_html)


if __name__ == "__main__":
    main()
