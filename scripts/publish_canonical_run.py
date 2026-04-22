from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import sys

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.canonical import (
    CANONICAL_BOUNDARY_PATH,
    CANONICAL_OUT_DIR,
    CANONICAL_RELEASE_METADATA_PATH,
    CANONICAL_RELEASE_NAME,
    CANONICAL_RELEASE_POINTER_PATH,
    CANONICAL_SCORES_PATH,
    CANONICAL_VERSION,
    CANONICAL_PREPARED_FLOOD_LAYER,
    CANONICAL_PREPARED_FLOOD_PATH,
    CANONICAL_PREPARED_PEAT_LAYER,
    CANONICAL_PREPARED_PEAT_PATH,
    canonical_release_payload,
)
from src.pipeline import build_mvp_outputs
from src.provenance import score_provenance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild and publish the canonical rewilding outputs from one scored run.",
    )
    parser.add_argument(
        "--scores-out-dir",
        type=Path,
        default=CANONICAL_OUT_DIR,
        help="Destination directory for the canonical scored run.",
    )
    parser.add_argument(
        "--boundary-path",
        type=Path,
        default=CANONICAL_BOUNDARY_PATH,
        help="Official England analysis boundary used for the canonical build.",
    )
    parser.add_argument(
        "--cell-diameter-m",
        type=float,
        default=1000,
        help="Hex cell diameter in metres.",
    )
    parser.add_argument(
        "--tile-size-m",
        type=float,
        default=50_000,
        help="Tile size used for chunked grid building and feature aggregation.",
    )
    parser.add_argument(
        "--scenario",
        default="scenario_balanced",
        choices=[
            "scenario_nature_first",
            "scenario_balanced",
            "scenario_low_conflict",
        ],
        help="Primary published shortlist scenario.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="Top ranked cells used for shortlist, clusters, validation, and inspection map.",
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Reuse cached canonical scores if they already exist instead of forcing a rebuild.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print pipeline progress while rebuilding the canonical scores.",
    )
    parser.add_argument(
        "--release-path",
        type=Path,
        default=CANONICAL_RELEASE_METADATA_PATH,
        help="Release checkpoint JSON emitted after a successful canonical publish run.",
    )
    parser.add_argument(
        "--skip-prepare-sources",
        action="store_true",
        help="Skip the canonical source simplification step and use existing prepared layers.",
    )
    return parser.parse_args()


def run_python_script(script_name: str, *script_args: object) -> None:
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / script_name)]
    command.extend(str(arg) for arg in script_args)
    subprocess.run(command, check=True, cwd=PROJECT_ROOT)


def git_head() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=PROJECT_ROOT,
                text=True,
            )
            .strip()
        )
    except subprocess.SubprocessError:
        return ""


def require_canonical_provenance(scores_path: Path) -> dict[str, str]:
    scores = gpd.read_parquet(scores_path)
    provenance = score_provenance(scores, scores_path)
    problems: list[str] = []

    if provenance.get("run_profile") != "canonical_published":
        problems.append(
            f"run_profile was `{provenance.get('run_profile', 'not recorded')}` instead of `canonical_published`"
        )
    if provenance.get("flood_feature_source") != "dedicated_dataset":
        problems.append(
            f"flood source was `{provenance.get('flood_feature_source', 'not recorded')}` instead of `dedicated_dataset`"
        )
    if provenance.get("peat_feature_source") != "dedicated_dataset":
        problems.append(
            f"peat source was `{provenance.get('peat_feature_source', 'not recorded')}` instead of `dedicated_dataset`"
        )

    if problems:
        joined = "; ".join(problems)
        raise RuntimeError(
            "Canonical publish step aborted because the scored layer does not satisfy the dedicated-source contract: "
            f"{joined}."
        )

    return provenance


def write_release_checkpoint(
    *,
    release_path: Path,
    scores_path: Path,
    run_metadata_path: Path,
    generated_outputs: dict[str, str],
    provenance: dict[str, str],
) -> None:
    payload = canonical_release_payload(generated_at=datetime.now(UTC).isoformat())
    payload["scores_path"] = str(scores_path)
    payload["run_metadata_path"] = str(run_metadata_path)
    payload["git_head"] = git_head()
    payload["provenance"] = provenance
    payload["generated_outputs"] = generated_outputs

    release_path.parent.mkdir(parents=True, exist_ok=True)
    release_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    CANONICAL_RELEASE_POINTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    CANONICAL_RELEASE_POINTER_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()

    if not args.skip_prepare_sources:
        run_python_script("prepare_canonical_sources.py")

    try:
        outputs = build_mvp_outputs(
            out_dir=args.scores_out_dir,
            boundary_path=args.boundary_path,
            flood_path=CANONICAL_PREPARED_FLOOD_PATH,
            flood_layer=CANONICAL_PREPARED_FLOOD_LAYER,
            peat_path=CANONICAL_PREPARED_PEAT_PATH,
            peat_layer=CANONICAL_PREPARED_PEAT_LAYER,
            cell_diameter_m=args.cell_diameter_m,
            tile_size_m=args.tile_size_m,
            verbose=args.verbose,
            reuse_existing=args.reuse_existing,
            require_dedicated_flood_peat=True,
            run_profile="canonical_published",
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "Canonical publish could not start because required dedicated inputs are missing locally. "
            f"{exc}"
        ) from exc

    scores_path = outputs.get("scores", CANONICAL_SCORES_PATH)
    run_metadata_path = outputs["run_metadata"]
    provenance = require_canonical_provenance(scores_path)

    top_candidates_csv = Path("outputs/top_candidates_1km") / f"{args.scenario}_top_{args.top_n}.csv"
    top_candidates_summary = Path("outputs/top_candidates_1km") / f"{args.scenario}_top_{args.top_n}_summary.md"
    cluster_csv = Path("outputs/candidate_clusters") / f"{args.scenario}_top_{args.top_n}_clusters.csv"
    cluster_geojson = Path("outputs/candidate_clusters") / f"{args.scenario}_top_{args.top_n}_clusters.geojson"
    cluster_summary = Path("outputs/candidate_clusters") / f"{args.scenario}_top_{args.top_n}_clusters_summary.md"
    inspection_map = Path("outputs/maps") / f"{args.scenario}_top_{args.top_n}_map.html"
    validation_summary = Path("outputs/validation/validation_summary.md")
    candidate_brief = Path("outputs/candidate_brief.md")
    methods_note = Path("outputs/methods.md")
    map_app = Path("outputs/app/rewilding_opportunity_explorer.html")

    run_python_script(
        "export_top_candidates.py",
        "--scores-path",
        scores_path,
        "--scenario",
        args.scenario,
        "--top-n",
        args.top_n,
    )
    run_python_script(
        "summarize_candidate_clusters.py",
        "--scores-path",
        scores_path,
        "--scenario",
        args.scenario,
        "--top-n",
        args.top_n,
    )
    run_python_script(
        "build_candidate_brief.py",
        "--cluster-summary-path",
        cluster_csv,
        "--clusters-geojson-path",
        cluster_geojson,
        "--scores-path",
        scores_path,
        "--scenario",
        args.scenario,
        "--release-path",
        args.release_path,
    )
    run_python_script(
        "validate_enriched_model.py",
        "--scores-path",
        scores_path,
        "--top-n",
        args.top_n,
    )
    run_python_script(
        "build_methods_note.py",
        "--scores-path",
        scores_path,
        "--top-candidates-summary-path",
        top_candidates_summary,
        "--cluster-summary-path",
        cluster_summary,
        "--validation-summary-path",
        validation_summary,
        "--app-path",
        map_app,
    )
    run_python_script(
        "build_inspection_map.py",
        "--scores-path",
        scores_path,
        "--scenario",
        args.scenario,
        "--top-n",
        args.top_n,
        "--out-html",
        inspection_map,
        "--clusters-path",
        cluster_geojson,
        "--cluster-summary-path",
        cluster_csv,
    )
    run_python_script(
        "build_map_app.py",
        "--scores-path",
        scores_path,
    )

    generated_outputs = {
        "top_candidates_csv": str(top_candidates_csv),
        "top_candidates_summary": str(top_candidates_summary),
        "cluster_csv": str(cluster_csv),
        "cluster_geojson": str(cluster_geojson),
        "cluster_summary": str(cluster_summary),
        "candidate_brief": str(candidate_brief),
        "methods_note": str(methods_note),
        "validation_summary": str(validation_summary),
        "inspection_map": str(inspection_map),
        "map_app": str(map_app),
    }
    write_release_checkpoint(
        release_path=args.release_path,
        scores_path=scores_path,
        run_metadata_path=run_metadata_path,
        generated_outputs=generated_outputs,
        provenance=provenance,
    )

    print(f"release_name: {CANONICAL_RELEASE_NAME}")
    print(f"version: {CANONICAL_VERSION}")
    print(f"scores: {scores_path}")
    print(f"run_metadata: {run_metadata_path}")
    print(f"release_checkpoint: {args.release_path}")


if __name__ == "__main__":
    main()
