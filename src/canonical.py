from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


CANONICAL_VERSION = "v6"
CANONICAL_RELEASE_NAME = f"canonical_{CANONICAL_VERSION}"

CANONICAL_BOUNDARY_PATH = Path("data/raw/boundaries/england_boundary_analysis.parquet")
CANONICAL_FLOOD_PATH = Path("data/raw/flood/ea_flood_zones.gpkg")
CANONICAL_FLOOD_LAYER = "Flood_Zones_2_3_Rivers_and_Sea"
CANONICAL_PEAT_PATH = Path("data/raw/peat/england_peat_map.gdb")
CANONICAL_PEAT_LAYER = "peaty_soil_extent_v1"
CANONICAL_PREPARED_DIR = Path("data/interim/canonical_sources")
CANONICAL_PREPARED_FLOOD_PATH = CANONICAL_PREPARED_DIR / "ea_flood_zones_simplified.parquet"
CANONICAL_PREPARED_FLOOD_LAYER = ""
CANONICAL_PREPARED_PEAT_PATH = CANONICAL_PREPARED_DIR / "england_peat_map_simplified.parquet"
CANONICAL_PREPARED_PEAT_LAYER = ""

CANONICAL_OUT_DIR = Path(f"data/interim/mvp_official_boundary_1km_{CANONICAL_VERSION}")
CANONICAL_SCORES_PATH = CANONICAL_OUT_DIR / "hex_scores.parquet"
CANONICAL_RUN_METADATA_PATH = CANONICAL_OUT_DIR / "run_metadata.json"
CANONICAL_RELEASE_DIR = Path("outputs/release")
CANONICAL_RELEASE_METADATA_PATH = CANONICAL_RELEASE_DIR / f"{CANONICAL_RELEASE_NAME}.json"
CANONICAL_RELEASE_POINTER_PATH = CANONICAL_RELEASE_DIR / "latest.json"


def canonical_source_contract() -> dict[str, object]:
    return {
        "version": CANONICAL_VERSION,
        "release_name": CANONICAL_RELEASE_NAME,
        "profile": "canonical_published",
        "boundary_path": str(CANONICAL_BOUNDARY_PATH),
        "flood_path": str(CANONICAL_FLOOD_PATH),
        "flood_layer": CANONICAL_FLOOD_LAYER,
        "peat_path": str(CANONICAL_PEAT_PATH),
        "peat_layer": CANONICAL_PEAT_LAYER,
        "prepared_flood_path": str(CANONICAL_PREPARED_FLOOD_PATH),
        "prepared_flood_layer": CANONICAL_PREPARED_FLOOD_LAYER,
        "prepared_peat_path": str(CANONICAL_PREPARED_PEAT_PATH),
        "prepared_peat_layer": CANONICAL_PREPARED_PEAT_LAYER,
        "scores_path": str(CANONICAL_SCORES_PATH),
        "requires_dedicated_flood_peat": True,
        "fallback_policy": "Development runs may fall back to CORINE proxies, but the canonical published run may not.",
    }


def canonical_release_payload(*, generated_at: str | None = None) -> dict[str, object]:
    return {
        "release_name": CANONICAL_RELEASE_NAME,
        "version": CANONICAL_VERSION,
        "generated_at_utc": generated_at or datetime.now(UTC).isoformat(),
        "scores_path": str(CANONICAL_SCORES_PATH),
        "run_metadata_path": str(CANONICAL_RUN_METADATA_PATH),
        "source_contract": canonical_source_contract(),
    }
