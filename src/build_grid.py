from __future__ import annotations

from math import cos, pi, sin, sqrt
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, box

from src.ingest import ensure_bng, repair_geometries


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
    checkpoint_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Create a hex grid clipped to a boundary geometry in BNG.

    The grid is built tile-by-tile to keep the expensive overlay step bounded.
    """

    boundary = ensure_bng(boundary)
    simplify_tolerance_m = max(50.0, min(500.0, cell_diameter_m / 4))
    clipping_boundary = boundary.copy()
    clipping_boundary["geometry"] = clipping_boundary.geometry.simplify(
        simplify_tolerance_m,
        preserve_topology=True,
    )
    clipping_boundary = repair_geometries(
        clipping_boundary,
        allowed_geom_types=("Polygon", "MultiPolygon"),
    )

    minx, miny, maxx, maxy = clipping_boundary.total_bounds
    boundary_geom = clipping_boundary.union_all()

    tile_counter = 0
    memory_parts: list[gpd.GeoDataFrame] = []
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            tile_counter += 1
            tile_path = checkpoint_dir / f"tile_{tile_counter:05d}.parquet" if checkpoint_dir is not None else None
            if tile_path is not None and tile_path.exists():
                if verbose:
                    existing = gpd.read_parquet(tile_path)
                    print(f"[grid] tile {tile_counter}: reuse {len(existing)} cells", flush=True)
                y += tile_size_m
                continue

            tile_geom = box(x, y, min(x + tile_size_m, maxx), min(y + tile_size_m, maxy))
            if not boundary_geom.intersects(tile_geom):
                if tile_path is not None:
                    empty = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=boundary.crs)
                    empty.to_parquet(tile_path)
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
                if tile_path is not None:
                    empty = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=boundary.crs)
                    empty.to_parquet(tile_path)
                y += tile_size_m
                continue

            chunk = chunk[chunk.geometry.intersects(boundary_geom)].copy()
            if chunk.empty:
                if tile_path is not None:
                    empty = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=boundary.crs)
                    empty.to_parquet(tile_path)
                y += tile_size_m
                continue

            boundary_hits = list(clipping_boundary.sindex.intersection(tile_geom.bounds))
            if not boundary_hits:
                if tile_path is not None:
                    empty = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=boundary.crs)
                    empty.to_parquet(tile_path)
                y += tile_size_m
                continue

            boundary_subset = clipping_boundary.iloc[boundary_hits][["geometry"]].copy()
            boundary_subset = boundary_subset[boundary_subset.geometry.intersects(tile_geom.buffer(cell_diameter_m))].copy()
            if boundary_subset.empty:
                if tile_path is not None:
                    empty = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=boundary.crs)
                    empty.to_parquet(tile_path)
                y += tile_size_m
                continue

            clipped = gpd.overlay(chunk, boundary_subset, how="intersection")
            clipped = clipped[
                ~clipped.geometry.is_empty
                & clipped.geometry.is_valid
                & clipped.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
                & (clipped.geometry.area > 1.0)
            ].copy()
            if tile_path is not None:
                clipped.to_parquet(tile_path)
            else:
                memory_parts.append(clipped)
            if verbose:
                print(
                    f"[grid] tile {tile_counter}: kept {len(clipped)} cells",
                    flush=True,
                )
            y += tile_size_m
        x += tile_size_m

    if checkpoint_dir is not None:
        tile_paths = sorted(checkpoint_dir.glob("tile_*.parquet"))
        grid_parts = [gpd.read_parquet(path) for path in tile_paths if path.stat().st_size > 0]
    else:
        grid_parts = memory_parts

    non_empty_parts = [part for part in grid_parts if not part.empty]
    if not non_empty_parts:
        return gpd.GeoDataFrame({"hex_id": [], "geometry": []}, geometry="geometry", crs=boundary.crs)

    grid = gpd.GeoDataFrame(
        pd.concat(non_empty_parts, ignore_index=True),
        geometry="geometry",
        crs=boundary.crs,
    )
    grid = grid.reset_index(drop=True)
    grid["hex_id"] = [f"hex_{i:07d}" for i in range(1, len(grid) + 1)]
    return grid[["hex_id", "geometry"]]
