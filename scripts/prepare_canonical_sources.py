from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
import pyogrio
import shapely
from shapely.geometry import box

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import (
    CANONICAL_FLOOD_LAYER,
    CANONICAL_FLOOD_PATH,
    CANONICAL_PEAT_LAYER,
    CANONICAL_PEAT_PATH,
    CANONICAL_PREPARED_FLOOD_PATH,
    CANONICAL_PREPARED_PEAT_PATH,
)
from src.ingest import repair_geometries, write_geoparquet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare simplified dedicated flood and peat layers for the canonical published run.",
    )
    parser.add_argument(
        "--flood-src",
        type=Path,
        default=CANONICAL_FLOOD_PATH,
        help="Raw dedicated flood source path.",
    )
    parser.add_argument(
        "--flood-layer",
        type=str,
        default=CANONICAL_FLOOD_LAYER,
        help="Flood layer name in the raw source.",
    )
    parser.add_argument(
        "--peat-src",
        type=Path,
        default=CANONICAL_PEAT_PATH,
        help="Raw dedicated peat source path.",
    )
    parser.add_argument(
        "--peat-layer",
        type=str,
        default=CANONICAL_PEAT_LAYER,
        help="Peat layer name in the raw source.",
    )
    parser.add_argument(
        "--flood-out",
        type=Path,
        default=CANONICAL_PREPARED_FLOOD_PATH,
        help="Prepared simplified flood output path.",
    )
    parser.add_argument(
        "--peat-out",
        type=Path,
        default=CANONICAL_PREPARED_PEAT_PATH,
        help="Prepared simplified peat output path.",
    )
    parser.add_argument(
        "--flood-tile-size-m",
        type=float,
        default=50_000,
        help="Tile size in metres used for flood simplification.",
    )
    parser.add_argument(
        "--peat-tile-size-m",
        type=float,
        default=100_000,
        help="Tile size in metres used for peat simplification.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild prepared layers even if they already exist.",
    )
    return parser.parse_args()


def iter_tile_bounds(bounds: tuple[float, float, float, float], tile_size_m: float) -> list[tuple[int, tuple[float, float, float, float]]]:
    minx, miny, maxx, maxy = bounds
    tiles: list[tuple[int, tuple[float, float, float, float]]] = []
    tile_id = 1
    x = minx
    while x < maxx:
        next_x = min(x + tile_size_m, maxx)
        y = miny
        while y < maxy:
            next_y = min(y + tile_size_m, maxy)
            tiles.append((tile_id, (x, y, next_x, next_y)))
            tile_id += 1
            y = next_y
        x = next_x
    return tiles


def load_bbox_frame(
    src: Path,
    *,
    layer: str,
    bbox: tuple[float, float, float, float],
    columns: list[str],
) -> gpd.GeoDataFrame:
    previous_organize = os.environ.get("OGR_ORGANIZE_POLYGONS")
    os.environ["OGR_ORGANIZE_POLYGONS"] = "SKIP"
    try:
        frame = pyogrio.read_dataframe(
            src,
            layer=layer,
            bbox=bbox,
            columns=columns,
            use_arrow=True,
        )
    finally:
        if previous_organize is None:
            os.environ.pop("OGR_ORGANIZE_POLYGONS", None)
        else:
            os.environ["OGR_ORGANIZE_POLYGONS"] = previous_organize
    return frame


def dissolve_clipped_tile(
    frame: gpd.GeoDataFrame,
    *,
    group_column: str,
    tile_bounds: tuple[float, float, float, float],
    tile_id: int,
) -> gpd.GeoDataFrame:
    if frame.empty:
        return frame.iloc[0:0].copy()

    # Raw dedicated sources can still contain a small number of invalid polygons.
    # Repair them before clipping so one bad feature does not abort the whole tile.
    frame = repair_geometries(frame, allowed_geom_types=("Polygon", "MultiPolygon"))
    if frame.empty:
        return frame

    tile_geom = box(*tile_bounds)
    clipped = frame.copy()
    clipped["geometry"] = shapely.intersection(clipped.geometry.array, tile_geom)
    clipped = clipped.loc[~clipped.geometry.is_empty & clipped.geometry.notna()].copy()
    if clipped.empty:
        return clipped

    rows: list[dict[str, object]] = []
    for value, group in clipped.groupby(group_column, dropna=False):
        unioned = shapely.union_all(group.geometry.to_list())
        if unioned is None or unioned.is_empty:
            continue
        rows.append(
            {
                group_column: value,
                "tile_id": tile_id,
                "geometry": unioned,
            }
        )

    return gpd.GeoDataFrame(rows, geometry="geometry", crs=frame.crs)


def simplify_layer_by_tiles(
    src: Path,
    *,
    layer: str,
    group_column: str,
    tile_size_m: float,
    verbose_label: str,
    checkpoint_dir: Path,
    force: bool,
) -> gpd.GeoDataFrame:
    info = pyogrio.read_info(src, layer=layer)
    bounds = tuple(float(value) for value in info["total_bounds"])
    crs = info["crs"]
    columns = [group_column]
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    for tile_id, tile_bounds in iter_tile_bounds(bounds, tile_size_m):
        checkpoint = checkpoint_dir / f"{verbose_label}_tile_{tile_id:04d}.parquet"
        if checkpoint.exists() and not force:
            print(f"[prepare:{verbose_label}] tile {tile_id}: reuse", flush=True)
            continue
        print(f"[prepare:{verbose_label}] tile {tile_id}: reading", flush=True)
        frame = load_bbox_frame(src, layer=layer, bbox=tile_bounds, columns=columns)
        if frame.empty:
            continue
        dissolved = dissolve_clipped_tile(
            frame,
            group_column=group_column,
            tile_bounds=tile_bounds,
            tile_id=tile_id,
        )
        if dissolved.empty:
            continue
        write_geoparquet(dissolved, checkpoint)
        print(
            f"[prepare:{verbose_label}] tile {tile_id}: {len(frame)} raw -> {len(dissolved)} simplified",
            flush=True,
        )

    tile_files = sorted(checkpoint_dir.glob(f"{verbose_label}_tile_*.parquet"))
    if not tile_files:
        return gpd.GeoDataFrame(columns=[group_column, "tile_id", "geometry"], geometry="geometry", crs=crs)

    combined = pd.concat([gpd.read_parquet(tile_file) for tile_file in tile_files], ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs=crs)


def prepare_flood(src: Path, layer: str, out_path: Path, *, force: bool, tile_size_m: float) -> None:
    if out_path.exists() and not force:
        return
    simplified = simplify_layer_by_tiles(
        src,
        layer=layer,
        group_column="flood_zone",
        tile_size_m=tile_size_m,
        verbose_label="flood",
        checkpoint_dir=out_path.parent / "flood_tiles",
        force=force,
    )
    write_geoparquet(simplified, out_path)


def prepare_peat(src: Path, layer: str, out_path: Path, *, force: bool, tile_size_m: float) -> None:
    if out_path.exists() and not force:
        return
    simplified = simplify_layer_by_tiles(
        src,
        layer=layer,
        group_column="DN",
        tile_size_m=tile_size_m,
        verbose_label="peat",
        checkpoint_dir=out_path.parent / "peat_tiles",
        force=force,
    )
    write_geoparquet(simplified, out_path)


def main() -> None:
    args = parse_args()

    if not args.flood_src.exists():
        raise SystemExit(f"Missing flood source: {args.flood_src}")
    if not args.peat_src.exists():
        raise SystemExit(f"Missing peat source: {args.peat_src}")

    prepare_flood(
        args.flood_src,
        args.flood_layer,
        args.flood_out,
        force=args.force,
        tile_size_m=args.flood_tile_size_m,
    )
    prepare_peat(
        args.peat_src,
        args.peat_layer,
        args.peat_out,
        force=args.force,
        tile_size_m=args.peat_tile_size_m,
    )

    print(f"prepared_flood: {args.flood_out}")
    print(f"prepared_peat: {args.peat_out}")


if __name__ == "__main__":
    main()
