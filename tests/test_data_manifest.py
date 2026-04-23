from __future__ import annotations

from pathlib import Path

from src.data_manifest import DEFAULT_MANIFEST_PATH, load_manifest, validate_manifest


def test_manifest_paths_exist_from_repo_root() -> None:
    entries, errors = validate_manifest(
        DEFAULT_MANIFEST_PATH,
        repo_root=Path.cwd(),
        allow_missing=True,
    )

    assert entries
    assert errors == []


def test_manifest_locks_current_official_result_artifact() -> None:
    entries = load_manifest(DEFAULT_MANIFEST_PATH)
    official = {entry.name: entry for entry in entries}

    assert official["england_boundary_analysis"].path == Path(
        "data/raw/boundaries/england_boundary_analysis.parquet"
    )
    assert official["flood_raw_dedicated"].path == Path("data/raw/flood/ea_flood_zones.gpkg")
    assert official["flood_raw_dedicated"].required is True
    assert official["peat_raw_dedicated"].path == Path("data/raw/peat/england_peat_map.gdb")
    assert official["peat_raw_dedicated"].required is True
    assert official["official_result_scores"].path == Path(
        "data/interim/mvp_official_boundary_1km_v6/hex_scores.parquet"
    )
