import geopandas as gpd

gdf = gpd.read_file("data/raw/corine/U2018_CLC2018_V2020_20u1.gpkg")

print(gdf.head())
print(gdf.columns)
print(gdf.crs)