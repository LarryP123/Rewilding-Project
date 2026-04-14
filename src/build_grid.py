from __future__ import annotations

from math import cos, pi, sin, sqrt

import geopandas as gpd
from shapely.geometry import Polygon

from src.ingest import ensure_bng


def _hexagon(cx: float, cy: float, radius: float) -> Polygon:
    return Polygon(
        [
            (
                cx + radius * cos(pi / 3 * i),
                cy + radius * sin(pi / 3 * i),
            )
            for i in range(6)
        ]
    )


def build_hex_grid(boundary: gpd.GeoDataFrame, cell_diameter_m: float = 1000) -> gpd.GeoDataFrame:
    """Create a hex grid clipped to a boundary geometry in BNG."""

    boundary = ensure_bng(boundary)
    minx, miny, maxx, maxy = boundary.total_bounds

    radius = cell_diameter_m / 2
    hex_height = sqrt(3) * radius
    x_step = 1.5 * radius
    y_step = hex_height

    hexes = []
    col = 0
    x = minx - cell_diameter_m
    while x <= maxx + cell_diameter_m:
        y_offset = 0 if col % 2 == 0 else hex_height / 2
        y = miny - hex_height
        while y <= maxy + hex_height:
            hexes.append(_hexagon(x, y + y_offset, radius))
            y += y_step
        x += x_step
        col += 1

    grid = gpd.GeoDataFrame({"geometry": hexes}, crs=boundary.crs)
    grid = gpd.overlay(grid, boundary[["geometry"]], how="intersection")
    grid = grid[
        ~grid.geometry.is_empty
        & grid.geometry.is_valid
        & grid.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        & (grid.geometry.area > 1.0)
    ].copy()
    grid = grid.reset_index(drop=True)
    grid["hex_id"] = [f"hex_{i:07d}" for i in range(1, len(grid) + 1)]
    return grid[["hex_id", "geometry"]]
