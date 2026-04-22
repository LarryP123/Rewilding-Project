from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

from src.pipeline import _resolve_named_asset
from src.provenance import score_provenance


def test_resolve_named_asset_requires_dedicated_when_requested(tmp_path: Path) -> None:
    missing = tmp_path / "missing.parquet"

    try:
        _resolve_named_asset(
            kind="flood",
            explicit_path=missing,
            explicit_layer=None,
            canonical_path=missing,
            candidates=(missing,),
            description="test asset",
            require_dedicated=True,
        )
    except FileNotFoundError as exc:
        assert "requires dedicated flood data" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing dedicated asset.")


def test_score_provenance_prefers_score_layer_columns(tmp_path: Path) -> None:
    scores_path = tmp_path / "hex_scores.parquet"
    gdf = gpd.GeoDataFrame(
        {
            "hex_id": ["hex_a"],
            "run_profile": ["canonical_published"],
            "flood_feature_source": ["dedicated_dataset"],
            "flood_source_path": ["data/raw/flood/ea_flood_zones.gpkg"],
            "peat_feature_source": ["dedicated_dataset"],
            "peat_source_path": ["data/raw/peat/england_peat_map.gdb"],
        },
        geometry=[Point(0, 0)],
        crs="EPSG:27700",
    )
    gdf.to_parquet(scores_path)

    provenance = score_provenance(gdf, scores_path)

    assert provenance["run_profile"] == "canonical_published"
    assert provenance["flood_feature_source"] == "dedicated_dataset"
    assert provenance["peat_feature_source"] == "dedicated_dataset"
