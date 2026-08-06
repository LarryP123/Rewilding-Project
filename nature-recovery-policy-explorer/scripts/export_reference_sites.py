"""Export BNG and Rewilding Network reference points for the MapLibre app.

Reads the root project's raw reference data (gitignored, fetched separately
per the root README) and writes small WGS84 GeoJSON files into data/publish/
for the app to load directly as point layers. Both inputs are optional: a
missing source is skipped rather than failing the build.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[2]
PUBLISH_DIR = Path(__file__).resolve().parents[1] / "data" / "publish"

BNG_SOURCE = ROOT / "data" / "raw" / "reference" / "bng_gain_sites.geojson"
RN_SOURCE = ROOT / "data" / "raw" / "reference" / "rewilding_network_projects.geojson"
ENGLAND_BOUNDARY = ROOT / "data" / "raw" / "boundaries" / "england_boundary.parquet"


def export_bng() -> None:
    if not BNG_SOURCE.exists():
        print(f"skipping BNG sites (not found): {BNG_SOURCE}")
        return
    sites = gpd.read_file(BNG_SOURCE)
    if sites.crs is None:
        sites = sites.set_crs("EPSG:4326")
    elif sites.crs.to_epsg() != 4326:
        sites = sites.to_crs("EPSG:4326")
    out_path = PUBLISH_DIR / "bng_sites.geojson"
    sites[["Reference", "geometry"]].to_file(out_path, driver="GeoJSON")
    print(f"wrote {len(sites)} BNG sites: {out_path}")


def export_rewilding_network() -> None:
    if not RN_SOURCE.exists():
        print(f"skipping Rewilding Network sites (not found): {RN_SOURCE}")
        return
    sites = gpd.read_file(RN_SOURCE)
    if sites.crs is None:
        sites = sites.set_crs("EPSG:4326")
    if "hideExactLocation" in sites.columns:
        sites = sites[~sites["hideExactLocation"].fillna(False)].copy()

    if ENGLAND_BOUNDARY.exists():
        boundary = gpd.read_parquet(ENGLAND_BOUNDARY)
        boundary = boundary.to_crs(sites.crs) if boundary.crs != sites.crs else boundary
        sites = gpd.sjoin(sites, boundary[["geometry"]], how="inner", predicate="within").drop(
            columns=["index_right"]
        )

    out_path = PUBLISH_DIR / "rewilding_network_sites.geojson"
    sites[["id", "geometry"]].to_file(out_path, driver="GeoJSON")
    print(f"wrote {len(sites)} Rewilding Network sites: {out_path}")


def main() -> None:
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    export_bng()
    export_rewilding_network()


if __name__ == "__main__":
    main()
