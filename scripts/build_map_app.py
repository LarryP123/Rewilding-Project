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

from src.geography import attach_geography_name
from src.score import SCENARIO_WEIGHTS


SCENARIO_LABELS = {
    "scenario_nature_first": "Nature-first",
    "scenario_balanced": "Balanced",
    "scenario_low_conflict": "Low-conflict",
}

SCENARIO_NOTES = {
    "scenario_nature_first": "Pushes hardest toward ecological recovery and restoration upside.",
    "scenario_balanced": "Keeps restoration central while holding space for flood, peat, and land-use tradeoffs.",
    "scenario_low_conflict": "Leans toward opportunities that look easier to unlock with lower agricultural tension.",
    "custom": "Your live weighting mix. Adjust the sliders to create and compare your own tradeoff lens.",
}

COMPONENT_LABELS = {
    "restoration_opportunity_score": "Restoration opportunity",
    "flood_opportunity_score_raw": "Flood opportunity",
    "peat_opportunity_score_raw": "Peat opportunity",
    "agri_opportunity_score_raw": "Agricultural opportunity",
    "habitat_mosaic_score": "Habitat mosaic",
    "bird_observation_score_raw": "Bird observation score",
}

SUPPLEMENTAL_METRICS = [
    ("connectivity_score", "Connectivity"),
    ("priority_habitat_share", "Priority habitat share (%)"),
    ("distance_to_priority_habitat_m", "Distance to habitat (m)"),
    ("cell_area_ratio", "Area ratio"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package shortlist outputs into a standalone user-facing map app.",
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km_v4/hex_scores.parquet"),
        help="Path to the scored national hex layer.",
    )
    parser.add_argument(
        "--boundary-path",
        type=Path,
        default=Path("data/raw/boundaries/england_boundary_analysis.parquet"),
        help="Boundary backdrop used for the national overview.",
    )
    parser.add_argument(
        "--top-n-per-scenario",
        type=int,
        default=250,
        help="Number of highest-scoring cells to keep per scenario before de-duplicating.",
    )
    parser.add_argument(
        "--top-n-per-component",
        type=int,
        default=120,
        help="Number of highest-scoring cells to keep per score component before de-duplicating.",
    )
    parser.add_argument(
        "--out-html",
        type=Path,
        default=Path("outouts/app/rewilding_opportunity_explorer.html"),
        help="Destination HTML file.",
    )
    parser.add_argument(
        "--admin-path",
        type=Path,
        default=Path("data/raw/reference/ons_counties_unitary_2024.geojson"),
        help="Administrative geography used to attach place names for case-study use.",
    )
    return parser.parse_args()


def available_component_columns(columns: list[str] | pd.Index) -> list[str]:
    ordered = list(dict.fromkeys(column for weights in SCENARIO_WEIGHTS.values() for column in weights))
    return [column for column in ordered if column in columns]


def normalized_weights(weights: dict[str, float], component_columns: list[str]) -> dict[str, float]:
    usable = {column: weights.get(column, 0.0) for column in component_columns}
    total = sum(usable.values())
    if total <= 0:
        equal = 1 / len(component_columns) if component_columns else 0
        return {column: equal for column in component_columns}
    return {column: value / total for column, value in usable.items()}


def make_projector(
    bounds: tuple[float, float, float, float],
    width: int = 1280,
    padding: int = 36,
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


def label_markup(
    gdf: gpd.GeoDataFrame,
    project: callable,
    *,
    label_column: str,
    css_class: str,
) -> list[str]:
    markup: list[str] = []
    for row in gdf.itertuples():
        if row.geometry is None or row.geometry.is_empty:
            continue
        point = row.geometry.representative_point()
        x, y = project(point.x, point.y)
        markup.append(
            f"""
            <text class="{css_class}" x="{x}" y="{y}" text-anchor="middle">{html.escape(str(getattr(row, label_column)))}</text>
            """
        )
    return markup


def build_shortlist(
    scores: gpd.GeoDataFrame,
    top_n_per_scenario: int,
    top_n_per_component: int,
    component_columns: list[str],
) -> gpd.GeoDataFrame:
    shortlisted: list[gpd.GeoDataFrame] = []
    ranks = scores[["hex_id"]].drop_duplicates().copy()

    for scenario in SCENARIO_WEIGHTS:
        ranked = scores.sort_values(scenario, ascending=False).head(top_n_per_scenario).copy()
        shortlisted.append(ranked)
        scenario_rank = (
            scores[["hex_id", scenario]]
            .sort_values(scenario, ascending=False)
            .reset_index(drop=True)
            .reset_index()
            .rename(columns={"index": f"{scenario}_rank"})
        )
        scenario_rank[f"{scenario}_rank"] = scenario_rank[f"{scenario}_rank"] + 1
        ranks = ranks.merge(scenario_rank[["hex_id", f"{scenario}_rank"]], on="hex_id", how="left")

    for column in component_columns:
        ranked = scores.sort_values(column, ascending=False).head(top_n_per_component).copy()
        shortlisted.append(ranked)

    combined = pd.concat(shortlisted, ignore_index=True)
    combined = combined.sort_values(
        ["scenario_balanced", "scenario_nature_first", "scenario_low_conflict"],
        ascending=False,
    ).drop_duplicates("hex_id")
    combined = combined.merge(
        ranks[
            [
                "hex_id",
                "scenario_nature_first_rank",
                "scenario_balanced_rank",
                "scenario_low_conflict_rank",
            ]
        ],
        on="hex_id",
        how="left",
    )
    return combined


def build_feature_payload(
    shortlist: gpd.GeoDataFrame,
    project: callable,
    component_columns: list[str],
) -> list[dict]:
    features: list[dict] = []
    for row in shortlist.itertuples():
        geom = row.geometry
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
            paths.append(exterior)

        representative = geom.representative_point()
        cx, cy = project(representative.x, representative.y)
        props = {
            "hex_id": row.hex_id,
            "scenario_nature_first": round(float(getattr(row, "scenario_nature_first", 0.0)), 2),
            "scenario_balanced": round(float(getattr(row, "scenario_balanced", 0.0)), 2),
            "scenario_low_conflict": round(float(getattr(row, "scenario_low_conflict", 0.0)), 2),
            "scenario_nature_first_rank": int(getattr(row, "scenario_nature_first_rank")),
            "scenario_balanced_rank": int(getattr(row, "scenario_balanced_rank")),
            "scenario_low_conflict_rank": int(getattr(row, "scenario_low_conflict_rank")),
            "priority_habitat_share": round(float(getattr(row, "priority_habitat_share", 0.0)), 2),
            "distance_to_priority_habitat_m": round(
                float(getattr(row, "distance_to_priority_habitat_m", 0.0)),
                1,
            ),
            "admin_name": (
                str(getattr(row, "admin_name"))
                if pd.notna(getattr(row, "admin_name", pd.NA))
                else ""
            ),
            "connectivity_score": round(float(getattr(row, "connectivity_score", 0.0)), 2),
            "undersized_cell_penalty": round(float(getattr(row, "undersized_cell_penalty", 1.0)), 4),
            "cell_area_ratio": round(float(getattr(row, "cell_area_ratio", 1.0)), 3),
            "cx": cx,
            "cy": cy,
        }
        for column in component_columns:
            value = getattr(row, column, 0.0)
            props[column] = round(float(value) if pd.notna(value) else 0.0, 2)

        features.append(
            {
                "hex_id": row.hex_id,
                "paths": paths,
                "cx": cx,
                "cy": cy,
                "properties": props,
            }
        )
    return features


def build_html(
    *,
    boundary_markup: list[str],
    county_markup: list[str],
    context_outline_markup: list[str],
    context_label_markup: list[str],
    features: list[dict],
    width: int,
    height: int,
    top_n_per_scenario: int,
    top_n_per_component: int,
    component_columns: list[str],
) -> str:
    initial_hex = features[0]["hex_id"]
    feature_lookup = {feature["hex_id"]: feature for feature in features}
    initial_props = feature_lookup[initial_hex]["properties"]

    presets = []
    for scenario_id, weights in SCENARIO_WEIGHTS.items():
        normalized = normalized_weights(weights, component_columns)
        presets.append(
            {
                "id": scenario_id,
                "label": SCENARIO_LABELS[scenario_id],
                "note": SCENARIO_NOTES[scenario_id],
                "weights": normalized,
            }
        )

    app_state = {
        "width": width,
        "height": height,
        "features": features,
        "components": [
            {"column": column, "label": COMPONENT_LABELS[column]}
            for column in component_columns
        ],
        "presets": presets,
        "initialMode": "scenario_balanced",
        "initialHexId": initial_hex,
        "shortlistCount": len(features),
        "topNPerScenario": top_n_per_scenario,
        "topNPerComponent": top_n_per_component,
    }
    app_state_json = json.dumps(app_state, separators=(",", ":")).replace("</", "<\\/")

    initial_component_cards = "".join(
        f"""
        <div class="metric-card">
          <div class="metric-label">{html.escape(COMPONENT_LABELS[column])}</div>
          <div class="metric-value">{initial_props[column]:.2f}</div>
        </div>
        """
        for column in component_columns
    )

    initial_support_cards = "".join(
        f"""
        <div class="metric-card metric-card-soft">
          <div class="metric-label">{html.escape(label)}</div>
          <div class="metric-value">{initial_props[column]:.2f}</div>
        </div>
        """
        for column, label in SUPPLEMENTAL_METRICS
    )
    initial_admin_name = initial_props["admin_name"] or "Place name unavailable"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Rewilding Opportunity Explorer</title>
  <style>
    :root {{
      --paper: #efe6d5;
      --panel: rgba(251, 247, 240, 0.94);
      --panel-strong: rgba(255, 252, 247, 0.98);
      --ink: #233128;
      --muted: #67746c;
      --line: rgba(62, 75, 66, 0.14);
      --accent: #2f6b4b;
      --accent-soft: rgba(47, 107, 75, 0.12);
      --warm: #bf8d3f;
      --warm-soft: rgba(191, 141, 63, 0.12);
      --map-bg: #e6dcc7;
      --shadow: 0 18px 48px rgba(21, 28, 25, 0.12);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.72), rgba(255,255,255,0) 36%),
        linear-gradient(180deg, #efe5d3 0%, #e3d8c2 100%);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
    }}
    .shell {{
      min-height: 100vh;
      padding: 20px;
      display: grid;
      grid-template-columns: minmax(0, 1.65fr) minmax(360px, 440px);
      gap: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }}
    .stage {{
      padding: 18px;
      display: grid;
      grid-template-rows: auto auto auto minmax(0, 1fr);
      gap: 16px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 14px;
      align-items: end;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0;
      font-family: "Iowan Old Style", "Georgia", serif;
      font-size: clamp(2rem, 4vw, 3.2rem);
      line-height: 0.94;
      letter-spacing: -0.02em;
    }}
    .hero p {{
      margin: 14px 0 0 0;
      color: var(--muted);
      max-width: 68ch;
      line-height: 1.5;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .summary-chip {{
      padding: 12px 14px;
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255,255,255,0.42));
      border: 1px solid var(--line);
    }}
    .summary-chip strong {{
      display: block;
      font-size: 1.06rem;
      margin-top: 3px;
    }}
    .summary-chip span {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .controls {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) repeat(3, minmax(0, 0.6fr));
      gap: 12px;
      align-items: stretch;
    }}
    .control-block {{
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 14px;
    }}
    .control-label {{
      display: block;
      margin-bottom: 8px;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .segmented {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .segmented button {{
      border: 1px solid rgba(47, 107, 75, 0.16);
      background: white;
      color: var(--ink);
      border-radius: 999px;
      padding: 10px 14px;
      font-size: 13px;
      cursor: pointer;
    }}
    .segmented button.active {{
      background: var(--accent);
      color: white;
      border-color: var(--accent);
    }}
    .range-row {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .range-row input[type="range"] {{
      width: 100%;
      accent-color: var(--accent);
    }}
    .range-value {{
      min-width: 42px;
      text-align: right;
      font-weight: 700;
    }}
    .control-block select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      background: white;
      font: inherit;
      color: inherit;
    }}
    .weighting-panel {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(240px, 300px);
      gap: 14px;
      padding: 16px;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.75), rgba(255,255,255,0.18)),
        linear-gradient(180deg, rgba(191,141,63,0.08), rgba(47,107,75,0.06));
      border: 1px solid var(--line);
      border-radius: 20px;
    }}
    .weighting-panel h2 {{
      margin: 0;
      font-size: 1.15rem;
    }}
    .weighting-panel p {{
      margin: 8px 0 0 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    .weight-sliders {{
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }}
    .slider-card {{
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255,255,255,0.66);
      border: 1px solid var(--line);
    }}
    .slider-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: baseline;
      margin-bottom: 8px;
    }}
    .slider-head strong {{
      font-size: 14px;
    }}
    .slider-head span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .slider-card input[type="range"] {{
      width: 100%;
      accent-color: var(--warm);
    }}
    .slider-meta {{
      margin-top: 8px;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .preset-stack {{
      display: grid;
      gap: 10px;
      align-content: start;
    }}
    .preset-card {{
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255,255,255,0.7);
      border: 1px solid var(--line);
    }}
    .preset-card.active {{
      border-color: rgba(47, 107, 75, 0.36);
      background: rgba(47, 107, 75, 0.1);
    }}
    .preset-card button {{
      width: 100%;
      text-align: left;
      border: 0;
      padding: 0;
      background: transparent;
      color: inherit;
      font: inherit;
      cursor: pointer;
    }}
    .preset-card strong {{
      display: block;
      margin-bottom: 4px;
    }}
    .preset-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }}
    .custom-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 8px 10px;
      font-size: 12px;
      font-weight: 700;
      background: var(--warm-soft);
      color: #8a652b;
    }}
    .map-card {{
      position: relative;
      overflow: hidden;
      padding: 14px;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.7), rgba(255,255,255,0.15)),
        linear-gradient(180deg, #f0e7d7 0%, #e1d6bf 100%);
      border: 1px solid var(--line);
      border-radius: 22px;
    }}
    .map-toolbar {{
      position: absolute;
      top: 24px;
      right: 24px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      z-index: 3;
    }}
    .map-toolbar button {{
      border: 1px solid var(--line);
      background: rgba(255, 253, 248, 0.92);
      border-radius: 999px;
      padding: 9px 12px;
      cursor: pointer;
      color: var(--ink);
      box-shadow: 0 10px 24px rgba(22, 29, 26, 0.08);
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 16px;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.72), rgba(255,255,255,0.22)),
        var(--map-bg);
      border: 1px solid rgba(63, 76, 67, 0.12);
      touch-action: none;
    }}
    .england-shape {{
      vector-effect: non-scaling-stroke;
      pointer-events: none;
    }}
    .county-line {{
      vector-effect: non-scaling-stroke;
      pointer-events: none;
      mix-blend-mode: multiply;
    }}
    .context-outline {{
      vector-effect: non-scaling-stroke;
      pointer-events: none;
    }}
    .context-label {{
      fill: rgba(35, 49, 40, 0.62);
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      paint-order: stroke;
      stroke: rgba(239, 230, 213, 0.95);
      stroke-width: 4px;
      stroke-linejoin: round;
      pointer-events: none;
    }}
    .cell {{
      cursor: pointer;
      vector-effect: non-scaling-stroke;
      transition: opacity 120ms ease, stroke-width 120ms ease;
    }}
    .cell.hidden {{
      opacity: 0.08;
      pointer-events: none;
    }}
    .cell.active {{
      stroke: #101713 !important;
      stroke-width: 2.6 !important;
      opacity: 1 !important;
    }}
    .map-note {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    .sidebar {{
      padding: 18px;
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
      gap: 14px;
      min-height: 0;
    }}
    .selected-card,
    .list-card {{
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
    }}
    .scenario-note {{
      color: var(--muted);
      line-height: 1.45;
      margin-top: 10px;
    }}
    .place-name {{
      margin-top: 6px;
      font-size: 15px;
      color: var(--accent);
      font-weight: 700;
    }}
    .selected-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .pill {{
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      padding: 7px 10px;
      font-size: 12px;
      font-weight: 700;
    }}
    .score-line {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
    }}
    .score-line strong {{
      font-size: 26px;
      line-height: 1;
      font-family: "Iowan Old Style", "Georgia", serif;
    }}
    .metric-grid {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .metric-card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(255,255,255,0.66);
    }}
    .metric-card-soft {{
      background: rgba(245, 242, 234, 0.95);
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.3;
      min-height: 30px;
    }}
    .metric-value {{
      margin-top: 6px;
      font-size: 20px;
      font-weight: 700;
    }}
    .section-title {{
      margin-top: 16px;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    .explain-list {{
      margin-top: 16px;
      display: grid;
      gap: 10px;
    }}
    .explain-row {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 11px 12px;
      background: rgba(255,255,255,0.72);
    }}
    .explain-head {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 10px;
      align-items: baseline;
      margin-bottom: 8px;
      font-size: 14px;
    }}
    .explain-head span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .bar-track {{
      height: 9px;
      border-radius: 999px;
      background: rgba(47, 107, 75, 0.12);
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #cb9c4a 0%, #708c43 58%, #2f6b4b 100%);
    }}
    .why-text {{
      margin-top: 14px;
      color: var(--muted);
      line-height: 1.5;
      font-size: 14px;
    }}
    .list-card {{
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      min-height: 0;
    }}
    .area-summary {{
      margin-bottom: 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .area-pill {{
      border-radius: 999px;
      background: rgba(191, 141, 63, 0.12);
      color: #87632c;
      padding: 7px 10px;
      font-size: 12px;
      font-weight: 700;
    }}
    .list-header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 10px;
    }}
    .list-header strong {{
      font-size: 18px;
    }}
    .shortlist {{
      overflow: auto;
      display: grid;
      gap: 8px;
      padding-right: 4px;
    }}
    .shortlist-item {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(255,255,255,0.64);
      cursor: pointer;
    }}
    .shortlist-item.active {{
      border-color: rgba(47, 107, 75, 0.4);
      background: rgba(47, 107, 75, 0.12);
    }}
    .shortlist-item-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 7px;
    }}
    .shortlist-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 1240px) {{
      .shell {{
        grid-template-columns: 1fr;
      }}
      .hero,
      .controls,
      .weighting-panel {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        grid-template-rows: auto auto auto;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="panel stage">
      <div class="hero">
        <div>
          <div class="eyebrow">User-facing screening app</div>
          <h1>Rewilding Opportunity Explorer</h1>
          <p>Browse a packaged shortlist built from the top {top_n_per_scenario} cells in each scenario plus the top {top_n_per_component} cells for each component signal. Compare preset tradeoff lenses, then adjust the weights yourself to see how the map and shortlist change.</p>
        </div>
        <div class="summary-grid">
          <div class="summary-chip"><span>Packaged shortlist</span><strong id="summary-count">{len(features)} cells</strong></div>
          <div class="summary-chip"><span>Preset lenses</span><strong>{len(SCENARIO_WEIGHTS)} starting points</strong></div>
          <div class="summary-chip"><span>Weighted components</span><strong>{len(component_columns)} live sliders</strong></div>
          <div class="summary-chip"><span>Selection</span><strong id="summary-selection">{initial_hex}</strong></div>
        </div>
      </div>

      <div class="controls">
        <div class="control-block">
          <span class="control-label">Tradeoff lens</span>
          <div class="segmented" id="mode-buttons"></div>
        </div>
        <label class="control-block">
          <span class="control-label">Minimum score</span>
          <div class="range-row">
            <input id="score-filter" type="range" min="0" max="100" step="1" value="0" />
            <span class="range-value" id="score-filter-value">0</span>
          </div>
        </label>
        <label class="control-block">
          <span class="control-label">Minimum connectivity</span>
          <div class="range-row">
            <input id="connectivity-filter" type="range" min="0" max="100" step="1" value="0" />
            <span class="range-value" id="connectivity-filter-value">0</span>
          </div>
        </label>
        <label class="control-block">
          <span class="control-label">List size</span>
          <select id="list-size">
            <option value="15">Top 15</option>
            <option value="25" selected>Top 25</option>
            <option value="50">Top 50</option>
            <option value="100">Top 100</option>
          </select>
        </label>
      </div>

      <div class="weighting-panel">
        <div>
          <div class="eyebrow" style="margin-bottom:6px;">Weight workbench</div>
          <h2>Adjust the scoring mix</h2>
          <p id="weighting-note">Preset lenses load a starting mix. As soon as you move a slider, the app switches to a live custom lens and re-ranks every packaged cell.</p>
          <div class="weight-sliders" id="weight-sliders"></div>
        </div>
        <div class="preset-stack">
          <div class="custom-badge" id="weight-total">Weights sum to 100%</div>
          <div id="preset-cards"></div>
        </div>
      </div>

      <div class="map-card">
        <div class="map-toolbar">
          <button type="button" id="zoom-in">Zoom In</button>
          <button type="button" id="zoom-out">Zoom Out</button>
          <button type="button" id="zoom-selected">Zoom To Selected</button>
          <button type="button" id="reset-view">Reset</button>
        </div>
        <svg id="inspection-map" viewBox="0 0 {width} {height}" role="img" aria-label="Shortlisted rewilding opportunity cells in England">
          {"".join(context_outline_markup)}
          {"".join(context_label_markup)}
          {"".join(boundary_markup)}
          {"".join(county_markup)}
          <g id="cell-layer"></g>
        </svg>
        <div class="map-note">
          <span id="map-status">Showing the packaged shortlist.</span>
          <span>Mouse wheel zooms, drag pans, click a cell for the explanation panel.</span>
        </div>
      </div>
    </section>

    <aside class="panel sidebar">
      <section class="selected-card">
        <div class="eyebrow">Selected cell</div>
        <div class="score-line">
          <div>
            <div id="selected-hex" style="font-weight:700;font-size:1.15rem;">{initial_hex}</div>
            <div class="place-name" id="selected-place">{initial_admin_name}</div>
            <div class="scenario-note" id="scenario-note">{SCENARIO_NOTES['scenario_balanced']}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;">Score</div>
            <strong id="selected-score">{initial_props['scenario_balanced']:.2f}</strong>
          </div>
        </div>
        <div class="selected-meta">
          <div class="pill" id="selected-rank">Rank #1 in Balanced</div>
          <div class="pill" id="selected-area">Area ratio {initial_props['cell_area_ratio']:.3f}</div>
          <div class="pill" id="selected-penalty">Boundary factor {initial_props['undersized_cell_penalty']:.3f}</div>
        </div>
        <div class="section-title">Weighted components</div>
        <div class="metric-grid" id="weighted-metric-grid">{initial_component_cards}</div>
        <div class="section-title">Context signals</div>
        <div class="metric-grid" id="support-metric-grid">{initial_support_cards}</div>
        <div class="explain-list" id="explain-list"></div>
        <div class="why-text" id="why-text"></div>
      </section>

      <section class="list-card">
        <div class="list-header">
          <div>
            <div class="eyebrow" style="margin-bottom:4px;">Filtered shortlist</div>
            <strong id="list-title">Top Balanced cells</strong>
          </div>
          <span id="list-count" style="color:var(--muted);">25 shown</span>
        </div>
        <div class="area-summary" id="area-summary"></div>
        <div class="shortlist" id="shortlist"></div>
      </section>
    </aside>
  </div>

  <script id="app-state" type="application/json">{app_state_json}</script>
  <script>
    const APP = JSON.parse(document.getElementById('app-state').textContent);
    const modeButtons = document.getElementById('mode-buttons');
    const scoreFilter = document.getElementById('score-filter');
    const connectivityFilter = document.getElementById('connectivity-filter');
    const scoreFilterValue = document.getElementById('score-filter-value');
    const connectivityFilterValue = document.getElementById('connectivity-filter-value');
    const listSize = document.getElementById('list-size');
    const weightSliders = document.getElementById('weight-sliders');
    const presetCards = document.getElementById('preset-cards');
    const weightTotal = document.getElementById('weight-total');
    const weightingNote = document.getElementById('weighting-note');
    const cellLayer = document.getElementById('cell-layer');
    const shortlistEl = document.getElementById('shortlist');
    const mapStatus = document.getElementById('map-status');
    const listTitle = document.getElementById('list-title');
    const listCount = document.getElementById('list-count');
    const summarySelection = document.getElementById('summary-selection');
    const selectedHex = document.getElementById('selected-hex');
    const selectedPlace = document.getElementById('selected-place');
    const selectedScore = document.getElementById('selected-score');
    const selectedRank = document.getElementById('selected-rank');
    const selectedArea = document.getElementById('selected-area');
    const selectedPenalty = document.getElementById('selected-penalty');
    const scenarioNote = document.getElementById('scenario-note');
    const weightedMetricGrid = document.getElementById('weighted-metric-grid');
    const supportMetricGrid = document.getElementById('support-metric-grid');
    const explainList = document.getElementById('explain-list');
    const whyText = document.getElementById('why-text');
    const areaSummary = document.getElementById('area-summary');
    const svg = document.getElementById('inspection-map');

    const featureMap = new Map(APP.features.map((feature) => [feature.hex_id, feature]));
    const cellElements = new Map();
    const presetMap = new Map(APP.presets.map((preset) => [preset.id, preset]));
    const components = APP.components;
    const fullView = {{ x: 0, y: 0, width: APP.width, height: APP.height }};
    const supportMetrics = [
      ['connectivity_score', 'Connectivity'],
      ['priority_habitat_share', 'Priority habitat share (%)'],
      ['distance_to_priority_habitat_m', 'Distance to habitat (m)'],
      ['cell_area_ratio', 'Area ratio'],
    ];

    let view = {{ ...fullView }};
    let dragStart = null;
    let activeHexId = APP.initialHexId;
    let currentMode = APP.initialMode;
    let customWeights = {{ ...presetMap.get(APP.initialMode).weights }};
    let currentRankMap = new Map();

    function clamp(value, min, max) {{
      return Math.max(min, Math.min(max, value));
    }}

    function renderViewBox() {{
      svg.setAttribute('viewBox', `${{view.x}} ${{view.y}} ${{view.width}} ${{view.height}}`);
    }}

    function clampView() {{
      const maxX = fullView.x + fullView.width - view.width;
      const maxY = fullView.y + fullView.height - view.height;
      view.x = clamp(view.x, fullView.x, maxX);
      view.y = clamp(view.y, fullView.y, maxY);
    }}

    function zoomAt(factor, centerX, centerY) {{
      const nextWidth = clamp(view.width / factor, fullView.width / 36, fullView.width);
      const nextHeight = clamp(view.height / factor, fullView.height / 36, fullView.height);
      const relX = (centerX - view.x) / view.width;
      const relY = (centerY - view.y) / view.height;
      view.x = centerX - nextWidth * relX;
      view.y = centerY - nextHeight * relY;
      view.width = nextWidth;
      view.height = nextHeight;
      clampView();
      renderViewBox();
    }}

    function zoomToFeature(hexId, factor = 16) {{
      const feature = featureMap.get(hexId);
      if (!feature) return;
      view.width = clamp(fullView.width / factor, fullView.width / 36, fullView.width);
      view.height = clamp(fullView.height / factor, fullView.height / 36, fullView.height);
      view.x = feature.cx - view.width / 2;
      view.y = feature.cy - view.height / 2;
      clampView();
      renderViewBox();
    }}

    function colorFor(value, minValue, maxValue) {{
      const safeMax = maxValue <= minValue ? minValue + 1 : maxValue;
      const ratio = clamp((value - minValue) / (safeMax - minValue), 0, 1);
      const stops = [
        [240, 234, 220],
        [199, 162, 79],
        [111, 143, 61],
        [47, 107, 75],
      ];
      const scaled = ratio * (stops.length - 1);
      const index = Math.min(Math.floor(scaled), stops.length - 2);
      const local = scaled - index;
      const rgb = stops[index].map((channel, i) => Math.round(channel + (stops[index + 1][i] - channel) * local));
      return `rgb(${{rgb[0]}}, ${{rgb[1]}}, ${{rgb[2]}})`;
    }}

    function activeWeights() {{
      if (currentMode === 'custom') return customWeights;
      return presetMap.get(currentMode).weights;
    }}

    function activeLabel() {{
      if (currentMode === 'custom') return 'Custom';
      return presetMap.get(currentMode).label;
    }}

    function activeNote() {{
      if (currentMode === 'custom') return '{SCENARIO_NOTES["custom"]}';
      return presetMap.get(currentMode).note;
    }}

    function presetRankFor(feature) {{
      return feature.properties[`${{currentMode}}_rank`];
    }}

    function customScoreFor(feature) {{
      const props = feature.properties;
      const penalty = Number(props.undersized_cell_penalty ?? 1);
      let total = 0;
      Object.entries(customWeights).forEach(([column, weight]) => {{
        total += Number(props[column] || 0) * Number(weight || 0);
      }});
      return Number((total * penalty).toFixed(2));
    }}

    function scoreFor(feature) {{
      if (currentMode === 'custom') return customScoreFor(feature);
      return Number(feature.properties[currentMode] || 0);
    }}

    function rankedAllFeatures() {{
      const ranked = [...APP.features].sort((a, b) => {{
        const delta = scoreFor(b) - scoreFor(a);
        if (delta !== 0) return delta;
        if (currentMode !== 'custom') {{
          return presetRankFor(a) - presetRankFor(b);
        }}
        return a.hex_id.localeCompare(b.hex_id);
      }});
      currentRankMap = new Map(ranked.map((feature, index) => [feature.hex_id, index + 1]));
      return ranked;
    }}

    function rankFor(feature) {{
      if (currentMode === 'custom') return currentRankMap.get(feature.hex_id) || 0;
      return presetRankFor(feature);
    }}

    function filteredFeatures(rankedFeatures) {{
      const minScore = Number(scoreFilter.value);
      const minConnectivity = Number(connectivityFilter.value);
      return rankedFeatures
        .filter((feature) => scoreFor(feature) >= minScore)
        .filter((feature) => Number(feature.properties.connectivity_score || 0) >= minConnectivity);
    }}

    function scenarioBounds(features) {{
      const values = features.map((feature) => scoreFor(feature));
      return {{
        min: values.length ? Math.min(...values) : 0,
        max: values.length ? Math.max(...values) : 100,
      }};
    }}

    function contributionRows(feature) {{
      const props = feature.properties;
      const penalty = Number(props.undersized_cell_penalty ?? 1);
      const weights = activeWeights();
      return components
        .map((component) => {{
          const raw = Number(props[component.column] || 0);
          const weight = Number(weights[component.column] || 0);
          const weighted = raw * weight * penalty;
          return {{
            ...component,
            raw,
            weight,
            weighted,
          }};
        }})
        .sort((a, b) => b.weighted - a.weighted);
    }}

    function buildNarrative(feature, contributions) {{
      const props = feature.properties;
      const leaders = contributions.slice(0, 3).map((row) => row.label.toLowerCase());
      const fragments = [
        `This cell stands out under the ${{activeLabel().toLowerCase()}} lens because ${{leaders.join(', ')}} contribute most to the final score.`
      ];
      if (props.admin_name) {{
        fragments.push(`For case-study work, this shortlisted cell falls within ${{props.admin_name}}.`);
      }}
      if (props.priority_habitat_share >= 15) {{
        fragments.push(`It also sits close to existing habitat, with ${{props.priority_habitat_share.toFixed(1)}}% priority habitat in-cell and connectivity at ${{props.connectivity_score.toFixed(1)}}.`);
      }} else {{
        fragments.push(`Priority habitat share is modest at ${{props.priority_habitat_share.toFixed(1)}}%, so this is more of an adjacency and restoration bet than an already-intact habitat block.`);
      }}
      if (currentMode === 'custom') {{
        fragments.push(`Because this is a custom lens, moving any slider immediately changes both shortlist ranking and map coloring for every packaged candidate.`);
      }}
      if (props.undersized_cell_penalty < 1) {{
        fragments.push(`Its boundary factor is ${{props.undersized_cell_penalty.toFixed(3)}}, so the score is being scaled down for a clipped edge cell.`);
      }}
      return fragments.join(' ');
    }}

    function ensureNormalizedCustomWeights(changedColumn = null) {{
      const rawWeights = components.map((component) => [component.column, Number(customWeights[component.column] || 0)]);
      let total = rawWeights.reduce((sum, [, value]) => sum + value, 0);
      if (total <= 0) {{
        const equal = 1 / components.length;
        components.forEach((component) => {{
          customWeights[component.column] = equal;
        }});
        return;
      }}
      if (!changedColumn) {{
        rawWeights.forEach(([column, value]) => {{
          customWeights[column] = value / total;
        }});
        return;
      }}
      const changedValue = clamp(Number(customWeights[changedColumn] || 0), 0, 1);
      const others = components.filter((component) => component.column !== changedColumn);
      const othersTotal = others.reduce((sum, component) => sum + Number(customWeights[component.column] || 0), 0);
      customWeights[changedColumn] = changedValue;
      if (others.length === 0) return;
      if (othersTotal <= 0) {{
        const share = (1 - changedValue) / others.length;
        others.forEach((component) => {{
          customWeights[component.column] = share;
        }});
      }} else {{
        const scale = (1 - changedValue) / othersTotal;
        others.forEach((component) => {{
          customWeights[component.column] = Number(customWeights[component.column] || 0) * scale;
        }});
      }}
    }}

    function applyPreset(presetId, asCustom = false) {{
      const preset = presetMap.get(presetId);
      customWeights = {{ ...preset.weights }};
      ensureNormalizedCustomWeights();
      currentMode = asCustom ? 'custom' : presetId;
      render();
    }}

    function renderModeButtons() {{
      const modes = [...APP.presets.map((preset) => preset.id), 'custom'];
      modeButtons.innerHTML = modes.map((mode) => `
        <button type="button" class="${{mode === currentMode ? 'active' : ''}}" data-mode="${{mode}}">
          ${{mode === 'custom' ? 'Custom' : presetMap.get(mode).label}}
        </button>
      `).join('');
      modeButtons.querySelectorAll('[data-mode]').forEach((button) => {{
        button.addEventListener('click', () => {{
          const mode = button.dataset.mode;
          if (mode === 'custom') {{
            currentMode = 'custom';
            render();
            return;
          }}
          applyPreset(mode, false);
        }});
      }});
    }}

    function renderSliders() {{
      const weights = activeWeights();
      weightSliders.innerHTML = components.map((component) => {{
        const value = currentMode === 'custom'
          ? Number(customWeights[component.column] || 0)
          : Number(weights[component.column] || 0);
        return `
          <label class="slider-card">
            <div class="slider-head">
              <strong>${{component.label}}</strong>
              <span>${{Math.round(value * 100)}}%</span>
            </div>
            <input type="range" min="0" max="100" step="1" value="${{Math.round(Number(customWeights[component.column] || 0) * 100)}}" data-component="${{component.column}}">
            <div class="slider-meta">
              <span>${{currentMode === 'custom' ? 'Live custom weight' : 'Preset starting weight'}}</span>
              <span>${{Math.round(Number(customWeights[component.column] || 0) * 100)}}%</span>
            </div>
          </label>
        `;
      }}).join('');
      weightSliders.querySelectorAll('[data-component]').forEach((input) => {{
        input.addEventListener('input', () => {{
          const column = input.dataset.component;
          customWeights[column] = Number(input.value) / 100;
          ensureNormalizedCustomWeights(column);
          currentMode = 'custom';
          render();
        }});
      }});
      const total = Math.round(components.reduce((sum, component) => sum + Number(customWeights[component.column] || 0), 0) * 100);
      weightTotal.textContent = currentMode === 'custom'
        ? `Custom weights sum to ${{total}}%`
        : `Preset available to remix`;
    }}

    function renderPresetCards() {{
      presetCards.innerHTML = APP.presets.map((preset) => `
        <div class="preset-card${{preset.id === currentMode ? ' active' : ''}}">
          <button type="button" data-preset="${{preset.id}}">
            <strong>${{preset.label}}</strong>
            <p>${{preset.note}}</p>
          </button>
        </div>
      `).join('');
      presetCards.querySelectorAll('[data-preset]').forEach((button) => {{
        button.addEventListener('click', () => {{
          applyPreset(button.dataset.preset, true);
        }});
      }});
    }}

    function renderSelected(feature) {{
      const props = feature.properties;
      const score = scoreFor(feature);
      const rank = rankFor(feature);
      selectedHex.textContent = props.hex_id;
      selectedPlace.textContent = props.admin_name || 'Place name unavailable';
      selectedScore.textContent = score.toFixed(2);
      selectedRank.textContent = `Rank #${{rank}} in ${{activeLabel()}}`;
      selectedArea.textContent = `Area ratio ${{props.cell_area_ratio.toFixed(3)}}`;
      selectedPenalty.textContent = `Boundary factor ${{props.undersized_cell_penalty.toFixed(3)}}`;
      scenarioNote.textContent = activeNote();
      summarySelection.textContent = props.hex_id;

      weightedMetricGrid.innerHTML = components.map((component) => `
        <div class="metric-card">
          <div class="metric-label">${{component.label}}</div>
          <div class="metric-value">${{Number(props[component.column] || 0).toFixed(2)}}</div>
        </div>
      `).join('');

      supportMetricGrid.innerHTML = supportMetrics.map(([column, label]) => `
        <div class="metric-card metric-card-soft">
          <div class="metric-label">${{label}}</div>
          <div class="metric-value">${{Number(props[column] || 0).toFixed(2)}}</div>
        </div>
      `).join('');

      const contributions = contributionRows(feature);
      const maxContribution = Math.max(...contributions.map((row) => row.weighted), 1);
      explainList.innerHTML = contributions.map((row) => `
        <div class="explain-row">
          <div class="explain-head">
            <strong>${{row.label}}</strong>
            <span>${{Math.round(row.weight * 100)}}% weight</span>
            <span>+${{row.weighted.toFixed(2)}}</span>
          </div>
          <div class="bar-track"><div class="bar-fill" style="width:${{(row.weighted / maxContribution) * 100}}%"></div></div>
          <div style="margin-top:8px;color:var(--muted);font-size:13px;">Raw component score ${{row.raw.toFixed(2)}} after weighting and boundary adjustment.</div>
        </div>
      `).join('');
      whyText.textContent = buildNarrative(feature, contributions);
    }}

    function renderList(features) {{
      const limit = Number(listSize.value);
      const rows = features.slice(0, limit);
      const areaCounts = new Map();
      features.forEach((feature) => {{
        const name = feature.properties.admin_name;
        if (!name) return;
        areaCounts.set(name, (areaCounts.get(name) || 0) + 1);
      }});
      const topAreas = [...areaCounts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, 4);
      listTitle.textContent = `Top ${{activeLabel()}} cells`;
      listCount.textContent = `${{rows.length}} shown of ${{features.length}} matches`;
      areaSummary.innerHTML = topAreas.length
        ? topAreas.map(([name, count]) => `<div class="area-pill">${{name}} (${{count}})</div>`).join('')
        : `<div class="area-pill">No named areas available</div>`;
      shortlistEl.innerHTML = rows.map((feature) => {{
        const props = feature.properties;
        const isActive = props.hex_id === activeHexId ? ' active' : '';
        return `
          <button class="shortlist-item${{isActive}}" data-hex-id="${{props.hex_id}}" type="button">
            <div class="shortlist-item-head">
              <strong>${{props.admin_name || props.hex_id}}</strong>
              <span>${{scoreFor(feature).toFixed(2)}}</span>
            </div>
            <div class="shortlist-meta">
              <span>${{props.hex_id}}</span>
              <span>Rank #${{rankFor(feature)}}</span>
              <span>Connectivity ${{props.connectivity_score.toFixed(1)}}</span>
              <span>Habitat ${{props.priority_habitat_share.toFixed(1)}}%</span>
              <span>Area ${{props.cell_area_ratio.toFixed(3)}}</span>
            </div>
          </button>
        `;
      }}).join('');
      shortlistEl.querySelectorAll('[data-hex-id]').forEach((button) => {{
        button.addEventListener('click', () => {{
          activeHexId = button.dataset.hexId;
          render();
          zoomToFeature(activeHexId);
        }});
      }});
    }}

    function renderMap(features) {{
      const visible = new Set(features.map((feature) => feature.hex_id));
      const bounds = scenarioBounds(features.length ? features : APP.features);
      APP.features.forEach((feature) => {{
        const fill = colorFor(scoreFor(feature), bounds.min, bounds.max);
        const stroke = feature.properties.undersized_cell_penalty < 1 ? '#8c6735' : '#294a36';
        const opacity = visible.has(feature.hex_id) ? 0.88 : 0.08;
        (cellElements.get(feature.hex_id) || []).forEach((element) => {{
          element.setAttribute('fill', fill);
          element.setAttribute('stroke', stroke);
          element.setAttribute('stroke-width', visible.has(feature.hex_id) ? '1.1' : '0.8');
          element.setAttribute('fill-opacity', String(opacity));
          element.classList.toggle('hidden', !visible.has(feature.hex_id));
          element.classList.toggle('active', feature.hex_id === activeHexId);
        }});
      }});
      mapStatus.textContent = `${{features.length}} cells meet the current filters under the ${{activeLabel().toLowerCase()}} lens.`;
    }}

    function ensureActiveVisible(features) {{
      if (features.some((feature) => feature.hex_id === activeHexId)) return;
      if (features.length) {{
        activeHexId = features[0].hex_id;
        return;
      }}
      activeHexId = APP.initialHexId;
    }}

    function createCells() {{
      APP.features.forEach((feature) => {{
        feature.paths.forEach((points) => {{
          const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
          polygon.setAttribute('points', points);
          polygon.setAttribute('class', 'cell');
          polygon.dataset.hexId = feature.hex_id;
          polygon.addEventListener('click', () => {{
            activeHexId = feature.hex_id;
            render();
            zoomToFeature(feature.hex_id);
          }});
          cellLayer.appendChild(polygon);
          if (!cellElements.has(feature.hex_id)) {{
            cellElements.set(feature.hex_id, []);
          }}
          cellElements.get(feature.hex_id).push(polygon);
        }});
      }});
    }}

    function render() {{
      scoreFilterValue.textContent = scoreFilter.value;
      connectivityFilterValue.textContent = connectivityFilter.value;
      weightingNote.textContent = currentMode === 'custom'
        ? 'You are in live custom mode. Slider changes immediately recompute scores and rankings across the packaged shortlist.'
        : 'Preset lenses give you a comparison baseline. Use a preset card to copy one into the sliders, then adjust from there.';
      renderModeButtons();
      renderSliders();
      renderPresetCards();
      const ranked = rankedAllFeatures();
      const features = filteredFeatures(ranked);
      ensureActiveVisible(features);
      renderMap(features);
      renderList(features);
      const activeFeature = featureMap.get(activeHexId) || featureMap.get(APP.initialHexId);
      if (activeFeature) {{
        renderSelected(activeFeature);
      }}
    }}

    createCells();
    render();

    scoreFilter.addEventListener('input', render);
    connectivityFilter.addEventListener('input', render);
    listSize.addEventListener('change', render);

    svg.addEventListener('wheel', (event) => {{
      event.preventDefault();
      const point = svg.createSVGPoint();
      point.x = event.clientX;
      point.y = event.clientY;
      const cursor = point.matrixTransform(svg.getScreenCTM().inverse());
      zoomAt(event.deltaY < 0 ? 1.28 : 1 / 1.28, cursor.x, cursor.y);
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

    document.getElementById('zoom-in').addEventListener('click', () => zoomAt(1.28, view.x + view.width / 2, view.y + view.height / 2));
    document.getElementById('zoom-out').addEventListener('click', () => zoomAt(1 / 1.28, view.x + view.width / 2, view.y + view.height / 2));
    document.getElementById('zoom-selected').addEventListener('click', () => zoomToFeature(activeHexId));
    document.getElementById('reset-view').addEventListener('click', () => {{
      view = {{ ...fullView }};
      renderViewBox();
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    scores = gpd.read_parquet(args.scores_path)
    boundary = gpd.read_parquet(args.boundary_path)
    admin_context = gpd.read_file(args.admin_path)
    admin_context = admin_context.to_crs(boundary.crs) if admin_context.crs != boundary.crs else admin_context
    component_columns = available_component_columns(scores.columns)
    shortlist = build_shortlist(
        scores,
        top_n_per_scenario=args.top_n_per_scenario,
        top_n_per_component=args.top_n_per_component,
        component_columns=component_columns,
    )
    shortlist = shortlist[shortlist.geometry.notna() & ~shortlist.geometry.is_empty].copy()
    shortlist = attach_geography_name(
        shortlist,
        args.admin_path,
        join_key="hex_id",
        output_column="admin_name",
        name_column="CTYUA24NM",
    )

    width = 1280
    project, height = make_projector(tuple(boundary.total_bounds), width=width)
    features = build_feature_payload(shortlist, project, component_columns)
    boundary_markup = geometry_markup(
        boundary,
        project,
        fill="#d6ddc9",
        stroke="#8e9b86",
        stroke_width=1.4,
        fill_opacity=1.0,
        css_class="england-shape",
    )

    english_admins = admin_context[admin_context["CTYUA24CD"].astype(str).str.startswith("E")].copy()
    county_markup = geometry_markup(
        english_admins,
        project,
        fill="none",
        stroke="rgba(69, 84, 74, 0.28)",
        stroke_width=0.8,
        fill_opacity=0.0,
        css_class="county-line",
    )

    context_parts: list[gpd.GeoDataFrame] = []
    for prefix, label in [("W", "Wales"), ("S", "Scotland")]:
        subset = admin_context[admin_context["CTYUA24CD"].astype(str).str.startswith(prefix)].copy()
        if subset.empty:
            continue
        dissolved = gpd.GeoDataFrame(
            { "label": [label] },
            geometry=[subset.union_all()],
            crs=admin_context.crs,
        )
        context_parts.append(dissolved)
    context_geography = (
        pd.concat(context_parts, ignore_index=True)
        if context_parts
        else gpd.GeoDataFrame(columns=["label", "geometry"], geometry="geometry", crs=admin_context.crs)
    )
    context_outline_markup = geometry_markup(
        context_geography,
        project,
        fill="rgba(224, 218, 205, 0.35)",
        stroke="rgba(122, 132, 124, 0.48)",
        stroke_width=1.0,
        fill_opacity=1.0,
        css_class="context-outline",
    )
    context_label_markup = label_markup(
        context_geography,
        project,
        label_column="label",
        css_class="context-label",
    )
    html_out = build_html(
        boundary_markup=boundary_markup,
        county_markup=county_markup,
        context_outline_markup=context_outline_markup,
        context_label_markup=context_label_markup,
        features=features,
        width=width,
        height=height,
        top_n_per_scenario=args.top_n_per_scenario,
        top_n_per_component=args.top_n_per_component,
        component_columns=component_columns,
    )
    args.out_html.parent.mkdir(parents=True, exist_ok=True)
    args.out_html.write_text(html_out)
    print(args.out_html)


if __name__ == "__main__":
    main()
