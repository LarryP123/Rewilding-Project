from __future__ import annotations

import json
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "policy_explorer.duckdb"
PUBLISH_DIR = ROOT / "data" / "publish"


def export_assets() -> None:
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))
    con.execute("LOAD spatial")

    app_hexes_path = PUBLISH_DIR / "app_hexes.parquet"
    app_hexes_tiles_path = PUBLISH_DIR / "app_hexes_tiles.fgb"
    scenario_summary_path = PUBLISH_DIR / "scenario_summary.parquet"
    app_hexes_preview_path = PUBLISH_DIR / "app_hexes_preview.geojson"
    scenario_summary_json_path = PUBLISH_DIR / "scenario_summary.json"
    app_overview_json_path = PUBLISH_DIR / "app_overview.json"
    app_hex_points_json_path = PUBLISH_DIR / "app_hexes_points.json"
    tile_schema_path = PUBLISH_DIR / "tile_schema.json"
    manifest_path = PUBLISH_DIR / "publish_manifest.json"

    con.execute(
        f"""
        copy (
            select
                hex_id,
                ST_AsWKB(geometry) as geometry_wkb,
                best_scenario_id,
                best_scenario_label,
                best_weighted_score,
                worst_scenario_id,
                worst_scenario_label,
                worst_weighted_score,
                best_rank,
                worst_rank,
                rank_spread,
                best_percentile,
                worst_percentile,
                top_decile_scenario_count,
                stable_core_flag,
                contested_flag,
                restoration_opportunity_score,
                flood_opportunity_score_raw,
                peat_opportunity_score_raw,
                agri_opportunity_score_raw,
                habitat_mosaic_score,
                biodiversity_observation_score_raw,
                balanced_strategy_weighted_score,
                balanced_strategy_rank,
                balanced_strategy_percentile,
                carbon_restoration_weighted_score,
                carbon_restoration_rank,
                carbon_restoration_percentile,
                flood_resilience_weighted_score,
                flood_resilience_rank,
                flood_resilience_percentile,
                lower_conflict_weighted_score,
                lower_conflict_rank,
                lower_conflict_percentile,
                nature_recovery_weighted_score,
                nature_recovery_rank,
                nature_recovery_percentile
            from app_hexes
        ) to '{app_hexes_path.as_posix()}'
        (format parquet, compression zstd)
        """
    )

    con.execute(
        f"""
        copy (
            select
                hex_id,
                geometry,
                best_scenario_id,
                cast(best_rank as bigint) as best_rank,
                cast(rank_spread as bigint) as rank_spread,
                cast(stable_core_flag as boolean) as stable_core_flag,
                cast(contested_flag as boolean) as contested_flag,
                cast(balanced_strategy_percentile as double) as balanced_strategy_percentile,
                cast(carbon_restoration_percentile as double) as carbon_restoration_percentile,
                cast(flood_resilience_percentile as double) as flood_resilience_percentile,
                cast(lower_conflict_percentile as double) as lower_conflict_percentile,
                cast(nature_recovery_percentile as double) as nature_recovery_percentile
            from app_hexes
        ) to '{app_hexes_tiles_path.as_posix()}'
        (format gdal, driver 'FlatGeobuf')
        """
    )

    con.execute(
        f"""
        copy (
            select *
            from scenario_summary
        ) to '{scenario_summary_path.as_posix()}'
        (format parquet, compression zstd)
        """
    )

    con.execute(
        f"""
        copy (
            select
                hex_id,
                stable_core_flag,
                contested_flag,
                best_scenario_id,
                best_rank,
                rank_spread,
                ST_AsGeoJSON(geometry) as geometry
            from app_hexes
            where stable_core_flag or contested_flag
            order by stable_core_flag desc, contested_flag desc, best_rank asc
            limit 2500
        ) to '{app_hexes_preview_path.as_posix()}'
        (format gdal, driver 'GeoJSON')
        """
    )

    scenario_summary_rows = con.execute(
        """
        select *
        from scenario_summary
        order by scenario_id
        """
    ).fetchdf()
    scenario_summary_json_path.write_text(
        scenario_summary_rows.to_json(orient="records", indent=2),
        encoding="utf-8",
    )

    overview_row = con.execute(
        """
        select
            count(*) as hex_count,
            sum(case when stable_core_flag then 1 else 0 end) as stable_core_hex_count,
            sum(case when contested_flag then 1 else 0 end) as contested_hex_count,
            avg(rank_spread) as avg_rank_spread,
            min(rank_spread) as min_rank_spread,
            max(rank_spread) as max_rank_spread
        from app_hexes
        """
    ).fetchdf()
    app_overview_json_path.write_text(
        overview_row.to_json(orient="records", indent=2),
        encoding="utf-8",
    )

    points_rows = con.execute(
        """
        select
            hex_id,
            ST_X(ST_Centroid(geometry)) as x,
            ST_Y(ST_Centroid(geometry)) as y,
            best_scenario_id,
            best_rank,
            rank_spread,
            stable_core_flag,
            contested_flag,
            balanced_strategy_percentile,
            carbon_restoration_percentile,
            flood_resilience_percentile,
            lower_conflict_percentile,
            nature_recovery_percentile
        from app_hexes
        order by hex_id
        """
    ).fetchdf()
    compact_columns = ["h", "x", "y", "b", "r", "s", "c", "bs", "cr", "fr", "lc", "nr"]
    compact_rows = []
    for row in points_rows.itertuples(index=False):
        compact_rows.append(
            [
                row.hex_id,
                round(float(row.x), 1),
                round(float(row.y), 1),
                row.best_scenario_id,
                int(row.rank_spread),
                1 if bool(row.stable_core_flag) else 0,
                1 if bool(row.contested_flag) else 0,
                round(float(row.balanced_strategy_percentile), 1),
                round(float(row.carbon_restoration_percentile), 1),
                round(float(row.flood_resilience_percentile), 1),
                round(float(row.lower_conflict_percentile), 1),
                round(float(row.nature_recovery_percentile), 1),
            ]
        )
    app_hex_points_json_path.write_text(
        json.dumps({"columns": compact_columns, "rows": compact_rows}, separators=(",", ":")),
        encoding="utf-8",
    )

    tile_schema = {
        "source_name": "app_hexes_tiles",
        "geometry_type": "Polygon",
        "id_field": "hex_id",
        "tile_strategy": {
            "recommended_format": "pmtiles",
            "recommended_layer_name": "policy_hexes",
            "recommended_minzoom": 4,
            "recommended_maxzoom": 7,
            "simplification": 6,
            "max_tile_bytes": 200000,
            "max_features_per_tile": 80000,
        },
        "base_fields": [
            "hex_id",
            "best_scenario_id",
            "best_rank",
            "rank_spread",
            "stable_core_flag",
            "contested_flag",
        ],
        "component_fields": [],
        "scenario_fields": {
            "balanced_strategy": {
                "percentile": "balanced_strategy_percentile",
            },
            "carbon_restoration": {
                "percentile": "carbon_restoration_percentile",
            },
            "flood_resilience": {
                "percentile": "flood_resilience_percentile",
            },
            "lower_conflict": {
                "percentile": "lower_conflict_percentile",
            },
            "nature_recovery": {
                "percentile": "nature_recovery_percentile",
            },
        },
        "frontend_defaults": {
            "scenario": "balanced_strategy",
            "color_field_pattern": "{scenario}_percentile",
            "filters": ["stable_core_flag", "contested_flag"],
            "hover_fields": [
                "hex_id",
                "best_scenario_id",
                "best_rank",
                "rank_spread",
                "stable_core_flag",
                "contested_flag",
            ],
        },
    }
    tile_schema_path.write_text(json.dumps(tile_schema, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "database": DB_PATH.name,
        "exports": [
            "app_hexes.parquet",
            "app_hexes_tiles.fgb",
            "scenario_summary.parquet",
            "scenario_summary.json",
            "app_overview.json",
            "app_hexes_points.json",
            "app_hexes_preview.geojson",
            "tile_schema.json",
        ],
        "tables": {
            "app_hexes_rows": con.execute("select count(*) from app_hexes").fetchone()[0],
            "scenario_summary_rows": con.execute("select count(*) from scenario_summary").fetchone()[0],
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    con.close()


if __name__ == "__main__":
    export_assets()
