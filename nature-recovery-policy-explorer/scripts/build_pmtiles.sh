#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT="${ROOT}/data/publish/app_hexes_tiles.fgb"
OUTPUT="${ROOT}/data/publish/policy_hexes.pmtiles"
TEMP_4326="${ROOT}/data/publish/app_hexes_tiles_4326.fgb"
SRC_SRS="+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs +type=crs"

ogr2ogr \
  -f FlatGeobuf "${TEMP_4326}" "${INPUT}" \
  -s_srs "${SRC_SRS}" \
  -t_srs EPSG:4326 \
  -nlt MULTIPOLYGON

ogr2ogr \
  -f PMTiles "${OUTPUT}" "${TEMP_4326}" \
  -nln policy_hexes \
  -dsco NAME=policy_hexes \
  -dsco DESCRIPTION="Nature Recovery Policy Explorer hex layer" \
  -dsco MINZOOM=4 \
  -dsco MAXZOOM=7 \
  -dsco SIMPLIFICATION=0.2 \
  -dsco SIMPLIFICATION_MAX_ZOOM=0.05 \
  -dsco MAX_SIZE=2000000 \
  -dsco MAX_FEATURES=500000
