from __future__ import annotations

from pathlib import Path

import geopandas as gpd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = PROJECT_ROOT / "data/raw/boundaries/england_boundary_analysis.parquet"
CLUSTERS_PATH = PROJECT_ROOT / "outputs/candidate_clusters/scenario_balanced_top_100_clusters.geojson"
OUT_DIR = PROJECT_ROOT / "docs/assets"

TARGETS = {
    "cluster_01": ("case_map_cornwall.svg", "Cornwall"),
    "cluster_05": ("case_map_somerset.svg", "Somerset"),
    "cluster_10": ("case_map_northern_borderland.svg", "Northern Borderland"),
}


def projector(bounds: tuple[float, float, float, float], width: int, padding: int) -> tuple[callable, int]:
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


def polygon_points(geom, project: callable) -> list[str]:
    if geom.geom_type == "Polygon":
        polygons = [geom]
    elif geom.geom_type == "MultiPolygon":
        polygons = list(geom.geoms)
    else:
        return []

    points: list[str] = []
    for polygon in polygons:
        coords = " ".join(f"{x},{y}" for x, y in (project(px, py) for px, py in polygon.exterior.coords))
        points.append(coords)
    return points


def build_svg(boundary_geom, cluster_geom, label: str) -> str:
    width = 460
    padding = 24
    project, height = projector(boundary_geom.bounds, width, padding)

    boundary_markup = "\n".join(
        f'<polygon points="{points}" class="boundary" />' for points in polygon_points(boundary_geom, project)
    )
    cluster_markup = "\n".join(
        f'<polygon points="{points}" class="cluster" />' for points in polygon_points(cluster_geom, project)
    )
    cx, cy = project(cluster_geom.representative_point().x, cluster_geom.representative_point().y)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{label}">
  <style>
    .bg {{ fill: #f6efe1; }}
    .boundary {{ fill: #d8cfbc; stroke: #8d9a83; stroke-width: 1.1; }}
    .cluster {{ fill: #2f6848; stroke: #173625; stroke-width: 1.4; }}
    .dot {{ fill: #bf8641; stroke: #fff8ef; stroke-width: 3; }}
    .label {{ font: 700 16px Avenir Next, Segoe UI, sans-serif; fill: #1f4933; }}
  </style>
  <rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="20" />
  {boundary_markup}
  {cluster_markup}
  <circle class="dot" cx="{cx}" cy="{cy}" r="6.5" />
  <text class="label" x="24" y="34">{label}</text>
</svg>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    boundary = gpd.read_parquet(BOUNDARY_PATH).to_crs(27700).geometry.union_all().simplify(900)
    clusters = gpd.read_file(CLUSTERS_PATH).to_crs(27700).set_index("cluster_id")

    for cluster_id, (filename, label) in TARGETS.items():
        cluster_geom = clusters.loc[cluster_id].geometry.simplify(350)
        svg = build_svg(boundary, cluster_geom, label)
        (OUT_DIR / filename).write_text(svg, encoding="utf-8")
        print(f"wrote {filename}")


if __name__ == "__main__":
    main()
