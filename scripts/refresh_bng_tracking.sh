#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="/opt/miniconda3/bin/python3"
BNG_PATH="data/raw/reference/bng_gain_sites.geojson"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] refreshing BNG register snapshot"
curl -sf "https://services-eu1.arcgis.com/Y9jgVEvgymHqAYPW/arcgis/rest/services/BNGSitesTEST/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson" \
  -o "${BNG_PATH}.tmp"
mv "${BNG_PATH}.tmp" "$BNG_PATH"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] running BNG alignment analysis"
"$PYTHON_BIN" scripts/analyze_bng_alignment.py

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] done"
