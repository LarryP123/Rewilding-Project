from __future__ import annotations

from src.canonical import (
    CANONICAL_RELEASE_METADATA_PATH,
    CANONICAL_RELEASE_NAME,
    CANONICAL_RUN_METADATA_PATH,
    CANONICAL_SCORES_PATH,
    CANONICAL_VERSION,
    canonical_release_payload,
    canonical_source_contract,
)


def test_canonical_contract_and_release_payload_share_versioned_paths() -> None:
    contract = canonical_source_contract()
    payload = canonical_release_payload(generated_at="2026-04-17T00:00:00+00:00")

    assert contract["version"] == CANONICAL_VERSION
    assert contract["release_name"] == CANONICAL_RELEASE_NAME
    assert contract["scores_path"] == str(CANONICAL_SCORES_PATH)
    assert payload["release_name"] == CANONICAL_RELEASE_NAME
    assert payload["scores_path"] == str(CANONICAL_SCORES_PATH)
    assert payload["run_metadata_path"] == str(CANONICAL_RUN_METADATA_PATH)
    assert str(CANONICAL_VERSION) in str(CANONICAL_RELEASE_METADATA_PATH)
