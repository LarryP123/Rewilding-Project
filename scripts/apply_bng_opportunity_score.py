from __future__ import annotations

import argparse
from pathlib import Path
import sys

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import CANONICAL_SCORES_PATH
from src.features import add_bng_opportunity_score
from src.ingest import write_geoparquet
from src.provenance import score_provenance
from src.score import BNG_SCENARIO_WEIGHTS, apply_scenarios


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich an already-scored hex layer with a BNG market-proximity "
            "feature and the scenario_bng_aligned lens. Reads the canonical "
            "scored layer read-only and writes a separate augmented output; "
            "it does not touch the core national pipeline or canonical files."
        ),
    )
    parser.add_argument(
        "--scores-path",
        type=Path,
        default=CANONICAL_SCORES_PATH,
        help="Path to the scored hex layer to enrich.",
    )
    parser.add_argument(
        "--bng-path",
        type=Path,
        default=Path("data/raw/reference/bng_gain_sites.geojson"),
        help=(
            "Registered Biodiversity Gain Site polygons/points. There is no "
            "official bulk download yet, so this must be supplied manually "
            "(e.g. exported from individual register lookups)."
        ),
    )
    parser.add_argument(
        "--out-path",
        type=Path,
        default=Path("outputs/bng_aligned/hex_scores_bng_aligned.parquet"),
        help="Output path for the augmented scored layer.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of top scenario_bng_aligned hexes to print.",
    )
    parser.add_argument(
        "--tile-size-m",
        type=float,
        default=50_000,
        help="Tile size used for the chunked proximity computation.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress while computing the proximity feature.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.bng_path.exists():
        raise SystemExit(
            f"--bng-path {args.bng_path} does not exist. There is no official "
            "bulk download of the Biodiversity Gain Site Register yet, so this "
            "file must be supplied manually before scenario_bng_aligned can be "
            "computed."
        )

    scored = gpd.read_parquet(args.scores_path)
    provenance = score_provenance(scored, args.scores_path)

    bng_sites = gpd.read_file(args.bng_path)
    if bng_sites.crs is None:
        raise SystemExit(f"--bng-path {args.bng_path} has no CRS set; cannot join it onto the hex grid.")

    enriched = add_bng_opportunity_score(
        scored,
        bng_sites,
        tile_size_m=args.tile_size_m,
        verbose=args.verbose,
    )
    enriched = apply_scenarios(enriched, scenario_weights=BNG_SCENARIO_WEIGHTS)

    write_geoparquet(gpd.GeoDataFrame(enriched, geometry="geometry", crs=scored.crs), args.out_path)

    top = enriched.sort_values("scenario_bng_aligned", ascending=False).head(args.top_n)
    preview_columns = [
        "hex_id",
        "scenario_bng_aligned",
        "bng_opportunity_score_raw",
        "distance_to_bng_site_m",
        "restoration_opportunity_score",
    ]
    preview_columns = [column for column in preview_columns if column in top.columns]

    print(f"source: {args.scores_path} (run profile: {provenance['run_profile']})")
    print(f"bng sites: {args.bng_path} ({len(bng_sites)} features)")
    print(f"written: {args.out_path}")
    print()
    print(top[preview_columns].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
