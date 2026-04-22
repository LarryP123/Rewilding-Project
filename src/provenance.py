from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

from src.canonical import CANONICAL_RUN_METADATA_PATH


def first_unique_value(frame: gpd.GeoDataFrame, column: str, fallback: str = "") -> str:
    if column not in frame.columns:
        return fallback
    values = frame[column].dropna().astype(str).unique().tolist()
    return values[0] if values else fallback


def read_run_metadata(scores_path: Path) -> dict[str, object]:
    candidates = [
        scores_path.parent / "run_metadata.json",
        CANONICAL_RUN_METADATA_PATH,
    ]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return {}


def score_provenance(scores: gpd.GeoDataFrame, scores_path: Path) -> dict[str, str]:
    metadata = read_run_metadata(scores_path)
    active_sources = metadata.get("active_sources", {}) if isinstance(metadata, dict) else {}
    flood_meta = active_sources.get("flood", {}) if isinstance(active_sources, dict) else {}
    peat_meta = active_sources.get("peat", {}) if isinstance(active_sources, dict) else {}

    return {
        "run_profile": first_unique_value(
            scores,
            "run_profile",
            str(metadata.get("run_profile", "not recorded")),
        ),
        "flood_feature_source": first_unique_value(
            scores,
            "flood_feature_source",
            str(flood_meta.get("source_name", "not recorded")),
        ),
        "flood_source_path": first_unique_value(
            scores,
            "flood_source_path",
            str(flood_meta.get("path", "")),
        ),
        "flood_clean_path": first_unique_value(
            scores,
            "flood_clean_path",
            str(flood_meta.get("clean_path", "")),
        ),
        "peat_feature_source": first_unique_value(
            scores,
            "peat_feature_source",
            str(peat_meta.get("source_name", "not recorded")),
        ),
        "peat_source_path": first_unique_value(
            scores,
            "peat_source_path",
            str(peat_meta.get("path", "")),
        ),
        "peat_clean_path": first_unique_value(
            scores,
            "peat_clean_path",
            str(peat_meta.get("clean_path", "")),
        ),
        "run_metadata_path": str((scores_path.parent / "run_metadata.json")),
    }
