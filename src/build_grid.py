from __future__ import annotations

from math import cos, pi, sin, sqrt

import geopandas as gpd
from shapely.geometry import Polygon, box

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


def _generate_hexes_for_bounds(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    cell_diameter_m: float,
) -> list[Polygon]:
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
    return hexes


def build_hex_grid(
    boundary: gpd.GeoDataFrame,
    cell_diameter_m: float = 1000,
    tile_size_m: float = 50_000,
    verbose: bool = False,
) -> gpd.GeoDataFrame:
    """Create a hex grid clipped to a boundary geometry in BNG.

    The grid is built tile-by-tile to keep the expensive overlay step bounded.
    """

    boundary = ensure_bng(boundary)
    minx, miny, maxx, maxy = boundary.total_bounds
    boundary_geom = boundary.union_all()

    grid_parts: list[gpd.GeoDataFrame] = []
    tile_id = 0
    tile_counter = 0

    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            tile_counter += 1
            tile_geom = box(x, y, min(x + tile_size_m, maxx), min(y + tile_size_m, maxy))
            if not boundary_geom.intersects(tile_geom):
                y += tile_size_m
                continue

            hexes = _generate_hexes_for_bounds(
                x - cell_diameter_m,
                y - cell_diameter_m,
                min(x + tile_size_m, maxx) + cell_diameter_m,
                min(y + tile_size_m, maxy) + cell_diameter_m,
                cell_diameter_m,
            )
            chunk = gpd.GeoDataFrame({"geometry": hexes}, crs=boundary.crs)
            centroids = chunk.geometry.centroid
            chunk = chunk[centroids.intersects(tile_geom)].copy()
            if chunk.empty:
                y += tile_size_m
                continue

            chunk = chunk[chunk.geometry.intersects(boundary_geom)].copy()
            if chunk.empty:
                y += tile_size_m
                continue

            clipped = gpd.overlay(chunk, boundary[["geometry"]], how="intersection")
            clipped = clipped[
                ~clipped.geometry.is_empty
                & clipped.geometry.is_valid
                & clipped.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
                & (clipped.geometry.area > 1.0)
            ].copy()
            if not clipped.empty:
                clipped["tile_id"] = tile_id
                grid_parts.append(clipped)
                tile_id += 1
                if verbose:
                    print(
                        f"[grid] tile {tile_counter}: kept {len(clipped)} cells",
                        flush=True,
                    )
            y += tile_size_m
        x += tile_size_m

    if not grid_parts:
        return gpd.GeoDataFrame({"hex_id": [], "geometry": []}, geometry="geometry", crs=boundary.crs)

    grid = gpd.GeoDataFrame(
        gpd.pd.concat(grid_parts, ignore_index=True),
        geometry="geometry",
        crs=boundary.crs,
    )
    grid = grid.reset_index(drop=True)
    grid["hex_id"] = [f"hex_{i:07d}" for i in range(1, len(grid) + 1)]
    return grid[["hex_id", "geometry"]]
