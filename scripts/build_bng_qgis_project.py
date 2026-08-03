from __future__ import annotations

import argparse
from pathlib import Path
import sys
import uuid

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import CANONICAL_SCORES_PATH
from src.features import add_bng_opportunity_score

SRS_BLOCK = """<spatialrefsys nativeFormat="Wkt">
          <wkt>PROJCRS["OSGB36 / British National Grid",BASEGEOGCRS["OSGB36",DATUM["Ordnance Survey of Great Britain 1936",ELLIPSOID["Airy 1830",6377563.396,299.3249646,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4277]],CONVERSION["British National Grid",METHOD["Transverse Mercator",ID["EPSG",9807]],PARAMETER["Latitude of natural origin",49,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",-2,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.9996012717,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",400000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",-100000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["(E)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["(N)",north,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Engineering survey, topographic mapping."],AREA["United Kingdom (UK)"],BBOX[49.75,-9.01,61.01,2.01]],ID["EPSG",27700]]</wkt>
          <proj4>+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +units=m +no_defs</proj4>
          <srsid>2429</srsid>
          <srid>27700</srid>
          <authid>EPSG:27700</authid>
          <description>OSGB36 / British National Grid</description>
          <projectionacronym>tmerc</projectionacronym>
          <ellipsoidacronym>EPSG:7001</ellipsoidacronym>
          <geographicflag>false</geographicflag>
        </spatialrefsys>"""

# ColorBrewer 5-class Greens, used for both the QGIS renderer and the finished map legend.
GREENS = [
    (247, 252, 245),
    (199, 233, 192),
    (116, 196, 118),
    (49, 163, 84),
    (0, 109, 44),
]
BNG_POINT_COLOR = (215, 25, 28)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a QGIS project (GeoPackage + .qgs) comparing rewilding "
            "opportunity scores against registered BNG gain sites, for "
            "opening directly in QGIS."
        ),
    )
    parser.add_argument("--scores-path", type=Path, default=CANONICAL_SCORES_PATH)
    parser.add_argument("--bng-path", type=Path, default=Path("data/raw/reference/bng_gain_sites.geojson"))
    parser.add_argument("--scenario", default="scenario_balanced")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/qgis"))
    parser.add_argument("--classes", type=int, default=5, help="Number of quantile classes for the choropleth.")
    return parser.parse_args()


def fill_symbol(name: str, rgb: tuple[int, int, int], alpha: int = 255, outline: str = "0,0,0,0", outline_width: str = "0") -> str:
    r, g, b = rgb
    return f"""        <symbol type="fill" name="{name}" alpha="1" clip_to_extent="1" force_rhr="0">
          <layer class="SimpleFill" locked="0" enabled="1" pass="0">
            <Option type="Map">
              <Option type="QString" name="color" value="{r},{g},{b},{alpha}"/>
              <Option type="QString" name="outline_color" value="{outline}"/>
              <Option type="QString" name="outline_style" value="solid"/>
              <Option type="QString" name="outline_width" value="{outline_width}"/>
              <Option type="QString" name="style" value="solid"/>
            </Option>
          </layer>
        </symbol>
"""


def layer_block(layer_id: str, layer_name: str, gpkg_path: Path, gpkg_layer: str, geom_type: str, renderer_xml: str, extent: tuple[float, float, float, float]) -> str:
    return f"""    <maplayer type="vector" hasScaleBasedVisibilityFlag="0" geometry="{geom_type}">
      <extent>
        <xmin>{extent[0]}</xmin>
        <ymin>{extent[1]}</ymin>
        <xmax>{extent[2]}</xmax>
        <ymax>{extent[3]}</ymax>
      </extent>
      <id>{layer_id}</id>
      <datasource>{gpkg_path}|layername={gpkg_layer}</datasource>
      <layername>{layer_name}</layername>
      <srs>
        {SRS_BLOCK}
      </srs>
      <provider encoding="UTF-8">ogr</provider>
{renderer_xml}
    </maplayer>
"""


def build_hex_renderer(breaks: list[float]) -> str:
    symbols_xml = "".join(
        fill_symbol(str(i), GREENS[i], outline="0,0,0,0", outline_width="0") for i in range(len(GREENS))
    )
    ranges_xml = "".join(
        f'          <range lower="{breaks[i]}" upper="{breaks[i+1]}" label="{breaks[i]:.1f} - {breaks[i+1]:.1f}" render="true" symbol="{i}"/>\n'
        for i in range(len(breaks) - 1)
    )
    return f"""      <renderer-v2 type="graduatedSymbol" symbollevels="0" forceraster="0" attr="__SCENARIO_COLUMN__" graduatedMethod="GraduatedColor" enableorderby="0">
        <ranges>
{ranges_xml}        </ranges>
        <symbols>
{symbols_xml}        </symbols>
        <source-symbol>
{fill_symbol("0", (200, 200, 200))}        </source-symbol>
      </renderer-v2>
"""


BNG_RENDERER = f"""      <renderer-v2 type="singleSymbol" symbollevels="0" forceraster="0" enableorderby="0">
        <symbols>
          <symbol type="marker" name="0" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer class="SimpleMarker" locked="0" enabled="1" pass="0">
              <Option type="Map">
                <Option type="QString" name="color" value="{BNG_POINT_COLOR[0]},{BNG_POINT_COLOR[1]},{BNG_POINT_COLOR[2]},255"/>
                <Option type="QString" name="outline_color" value="35,35,35,255"/>
                <Option type="QString" name="outline_style" value="solid"/>
                <Option type="QString" name="outline_width" value="0.3"/>
                <Option type="QString" name="name" value="circle"/>
                <Option type="QString" name="size" value="2.6"/>
                <Option type="QString" name="size_unit" value="MM"/>
                <Option type="QString" name="horizontal_anchor_point" value="1"/>
                <Option type="QString" name="vertical_anchor_point" value="1"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
"""

BOUNDARY_RENDERER = f"""      <renderer-v2 type="singleSymbol" symbollevels="0" forceraster="0" enableorderby="0">
        <symbols>
{fill_symbol("0", (0, 0, 0), alpha=0, outline="70,70,70,255", outline_width="0.4")}        </symbols>
      </renderer-v2>
"""


def write_qgs_project(out_dir: Path, gpkg_path: Path, extent: tuple[float, float, float, float], scenario: str, breaks: list[float]) -> Path:
    hex_id = "hex_scores_" + uuid.uuid4().hex[:8]
    bng_id = "bng_sites_" + uuid.uuid4().hex[:8]
    boundary_id = "england_boundary_" + uuid.uuid4().hex[:8]

    hex_renderer = build_hex_renderer(breaks).replace("__SCENARIO_COLUMN__", scenario)

    layers_xml = (
        layer_block(hex_id, f"Rewilding Opportunity ({scenario})", gpkg_path, "hex_scores", "Polygon", hex_renderer, extent)
        + layer_block(boundary_id, "England Boundary", gpkg_path, "england_boundary", "Polygon", BOUNDARY_RENDERER, extent)
        + layer_block(bng_id, "Registered BNG Sites", gpkg_path, "bng_sites", "Point", BNG_RENDERER, extent)
    )

    qgs = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="BNG Alignment" version="3.44.12-Solothurn">
  <homePath path=""/>
  <title>Rewilding Opportunity vs Registered BNG Sites</title>
  <projectCrs>
    {SRS_BLOCK}
  </projectCrs>
  <layer-tree-group>
    <customproperties/>
    <layer-tree-layer id="{bng_id}" name="Registered BNG Sites" source="{gpkg_path}|layername=bng_sites" providerKey="ogr" checked="Qt::Checked" expanded="1"/>
    <layer-tree-layer id="{hex_id}" name="Rewilding Opportunity ({scenario})" source="{gpkg_path}|layername=hex_scores" providerKey="ogr" checked="Qt::Checked" expanded="1"/>
    <layer-tree-layer id="{boundary_id}" name="England Boundary" source="{gpkg_path}|layername=england_boundary" providerKey="ogr" checked="Qt::Checked" expanded="1"/>
  </layer-tree-group>
  <layerorder>
    <layer id="{bng_id}"/>
    <layer id="{hex_id}"/>
    <layer id="{boundary_id}"/>
  </layerorder>
  <projectlayers>
{layers_xml}  </projectlayers>
  <mapcanvas name="theMapCanvas">
    <extent>
      <xmin>{extent[0]}</xmin>
      <ymin>{extent[1]}</ymin>
      <xmax>{extent[2]}</xmax>
      <ymax>{extent[3]}</ymax>
    </extent>
    <rotation>0</rotation>
    <destinationsrs>
      {SRS_BLOCK}
    </destinationsrs>
  </mapcanvas>
  <projectMetadata>
    <title>Rewilding Opportunity vs Registered BNG Sites</title>
    <author>Laurence Pengelly</author>
  </projectMetadata>
</qgis>
"""
    out_path = out_dir / "bng_alignment.qgs"
    out_path.write_text(qgs)
    return out_path


def main() -> None:
    args = parse_args()
    if not args.bng_path.exists():
        raise SystemExit(f"--bng-path {args.bng_path} does not exist. See README for how to fetch it.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    scored = gpd.read_parquet(args.scores_path)
    bng = gpd.read_file(args.bng_path)
    enriched = add_bng_opportunity_score(scored, bng, tile_size_m=50_000)

    hexes = enriched[
        ["hex_id", "scenario_balanced", "scenario_nature_first", "scenario_low_conflict",
         "bng_opportunity_score_raw", "distance_to_bng_site_m", "geometry"]
    ].copy()
    hexes["near_bng_10km"] = hexes["distance_to_bng_site_m"] <= 10_000

    gpkg_path = (args.out_dir / "bng_alignment.gpkg").resolve()
    if gpkg_path.exists():
        gpkg_path.unlink()
    hexes.to_file(gpkg_path, layer="hex_scores", driver="GPKG")

    bng_out = bng.to_crs(hexes.crs)[["Reference", "LPA", "site_size", "geometry"]].copy()
    bng_out.to_file(gpkg_path, layer="bng_sites", driver="GPKG")

    boundary = gpd.read_parquet("data/raw/boundaries/england_boundary.parquet").to_crs(hexes.crs)
    boundary.to_file(gpkg_path, layer="england_boundary", driver="GPKG")

    breaks = list(hexes[args.scenario].quantile([i / args.classes for i in range(args.classes + 1)]))
    extent = tuple(hexes.total_bounds)

    qgs_path = write_qgs_project(args.out_dir, gpkg_path, extent, args.scenario, breaks)

    print(f"geopackage: {gpkg_path}")
    print(f"qgis project: {qgs_path}")
    print(f"sites: {len(bng_out)}")
    print(f"breaks ({args.scenario}): {[round(b, 2) for b in breaks]}")
    print()
    print("Open the project with:")
    print(f"  open -a QGIS {qgs_path}")


if __name__ == "__main__":
    main()
