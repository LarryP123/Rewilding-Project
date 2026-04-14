from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import build_mvp_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build MVP rewilding outputs using the official England boundary.",
    )
    parser.add_argument(
        "--cell-diameter-m",
        type=float,
        default=1000,
        help="Hex cell diameter in metres.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/interim/mvp_official_boundary_1km"),
        help="Output directory for generated layers.",
    )
    parser.add_argument(
        "--boundary-path",
        type=Path,
        default=Path("data/raw/boundaries/england_boundary_analysis.parquet"),
        help="Path to the official England boundary file.",
    )
    parser.add_argument(
        "--tile-size-m",
        type=float,
        default=50_000,
        help="Tile size used for chunked grid building and feature aggregation.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress while building the outputs.",
    )
    parser.add_argument(
        "--no-reuse-existing",
        action="store_true",
        help="Rebuild outputs even if cached intermediates already exist.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = build_mvp_outputs(
        out_dir=args.out_dir,
        boundary_path=args.boundary_path,
        cell_diameter_m=args.cell_diameter_m,
        tile_size_m=args.tile_size_m,
        verbose=args.verbose,
        reuse_existing=not args.no_reuse_existing,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
