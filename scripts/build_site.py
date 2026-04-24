from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"


ASSET_COPIES = {
    PROJECT_ROOT / "outputs/app/rewilding_opportunity_explorer.html": DOCS_DIR
    / "maps/rewilding_opportunity_explorer.html",
    PROJECT_ROOT / "outputs/maps/scenario_balanced_top_100_map.html": DOCS_DIR
    / "maps/scenario_balanced_top_100_map.html",
    PROJECT_ROOT / "outputs/candidate_brief.md": DOCS_DIR / "files/candidate_brief.md",
    PROJECT_ROOT / "outputs/methods.md": DOCS_DIR / "files/methods.md",
    PROJECT_ROOT / "outputs/validation/validation_summary.md": DOCS_DIR
    / "files/validation_summary.md",
    PROJECT_ROOT / "outputs/top_candidates_1km/scenario_balanced_top_100.csv": DOCS_DIR
    / "files/scenario_balanced_top_100.csv",
    PROJECT_ROOT / "outputs/top_candidates_1km/scenario_balanced_top_100.geojson": DOCS_DIR
    / "files/scenario_balanced_top_100.geojson",
    PROJECT_ROOT / "outputs/candidate_clusters/scenario_balanced_top_100_clusters.csv": DOCS_DIR
    / "files/scenario_balanced_top_100_clusters.csv",
    PROJECT_ROOT / "outputs/candidate_clusters/scenario_balanced_top_100_clusters.geojson": DOCS_DIR
    / "files/scenario_balanced_top_100_clusters.geojson",
    PROJECT_ROOT / "outputs/release/canonical_v6.json": DOCS_DIR / "files/canonical_v6.json",
}


def copy_if_present(source: Path, destination: Path) -> None:
    if not source.exists():
        print(f"missing: {source.relative_to(PROJECT_ROOT)}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"copied: {source.relative_to(PROJECT_ROOT)} -> {destination.relative_to(PROJECT_ROOT)}")


def main() -> None:
    for source, destination in ASSET_COPIES.items():
        copy_if_present(source, destination)


if __name__ == "__main__":
    main()
