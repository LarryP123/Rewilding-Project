from pathlib import Path
import geopandas as gpd
from shapely.geometry import box

RAW = Path("data/raw/corine/U2018_CLC2018_V2020_20u1.gpkg")
OUT_DIR = Path("data/interim")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LAYER = "U2018_CLC2018_V2020_20u1"

# England-ish bbox in WGS84
england_wgs84 = gpd.GeoSeries(
    [box(-6.5, 49.8, 2.2, 56.2)],
    crs="EPSG:4326"
)

# Convert bbox to CORINE CRS
england_3035 = england_wgs84.to_crs("EPSG:3035")
minx, miny, maxx, maxy = england_3035.total_bounds

print("Reading CORINE subset...")
gdf = gpd.read_file(
    RAW,
    layer=LAYER,
    bbox=(minx, miny, maxx, maxy),
)

print(f"Subset rows loaded: {len(gdf):,}")
print(f"Original CRS: {gdf.crs}")
print(f"Columns: {list(gdf.columns)}")

print("Reprojecting to EPSG:27700...")
gdf = gdf.to_crs(epsg=27700)

gdf.columns = gdf.columns.str.lower()

out_path = OUT_DIR / "corine_subset.parquet"
print(f"Saving to {out_path} ...")
gdf.to_parquet(out_path)

print("Done.")