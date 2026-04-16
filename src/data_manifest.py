from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib


DEFAULT_MANIFEST_PATH = Path("data/manifest.toml")


@dataclass(frozen=True)
class ManifestEntry:
    """A single data asset tracked by the repository manifest."""

    name: str
    path: Path
    description: str = ""
    stage: str = ""
    required: bool = True


def load_manifest(manifest_path: Path = DEFAULT_MANIFEST_PATH) -> list[ManifestEntry]:
    """Parse the TOML manifest into validated entries."""

    payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("dataset", [])
    if not entries:
        raise ValueError(f"No [[dataset]] entries found in {manifest_path}.")

    manifest_entries: list[ManifestEntry] = []
    for entry in entries:
        name = entry.get("name")
        path = entry.get("path")
        if not name or not path:
            raise ValueError("Each [[dataset]] entry must include both 'name' and 'path'.")
        manifest_entries.append(
            ManifestEntry(
                name=name,
                path=Path(path),
                description=entry.get("description", ""),
                stage=entry.get("stage", ""),
                required=bool(entry.get("required", True)),
            )
        )
    return manifest_entries


def validate_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    repo_root: Path | None = None,
    allow_missing: bool = False,
) -> tuple[list[ManifestEntry], list[str]]:
    """Return manifest entries plus any validation failures."""

    root = repo_root or Path.cwd()
    entries = load_manifest(manifest_path)
    errors: list[str] = []
    seen_names: set[str] = set()

    for entry in entries:
        if entry.name in seen_names:
            errors.append(f"{entry.name}: duplicate dataset name")
        seen_names.add(entry.name)

        if entry.path.is_absolute():
            errors.append(f"{entry.name}: manifest paths must be relative ({entry.path})")

        asset_path = root / entry.path
        if not allow_missing and entry.required and not asset_path.exists():
            errors.append(f"{entry.name}: missing required path {entry.path}")

    return entries, errors


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for CI and local validation."""

    args = argv or sys.argv[1:]
    allow_missing = False
    manifest_arg: str | None = None
    for arg in args:
        if arg == "--allow-missing":
            allow_missing = True
            continue
        manifest_arg = arg

    manifest_path = Path(manifest_arg) if manifest_arg is not None else DEFAULT_MANIFEST_PATH
    entries, errors = validate_manifest(manifest_path, allow_missing=allow_missing)

    if errors:
        print(f"Manifest check failed for {manifest_path} ({len(errors)} issue(s)):")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Manifest check passed for {manifest_path} ({len(entries)} dataset(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
