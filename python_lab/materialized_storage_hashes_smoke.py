#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def required_subset(required: Iterable[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def explicit_safety_flags_ok(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False)
    return (
        '"credential_values_present": true' not in serialized
        and '"recommendation_output_present": true' not in serialized
        and '"ready_for_training": true' not in serialized
    )


def is_sha256_hex(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def build_report(root: Path, manifest_path: Path, verification_path: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/materialized_storage_hashes.v441_v450.json")
    manifest = read_json(manifest_path)
    verification = read_json(verification_path)
    cargo = (root / "rust-core/Cargo.toml").read_text(encoding="utf-8")
    runner = (root / "rust-core/src/bin/omnibet-materialized-storage-hasher.rs").read_text(encoding="utf-8")
    docs = (root / "docs/materialized_storage_hashes_v441_v450.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v441_v450_materialized_storage_hashes.yml").read_text(encoding="utf-8")
    acceptance = contract.get("acceptance", {})
    artifacts = manifest.get("artifacts", [])
    record_required = contract.get("artifact_record_required_fields", [])

    compressed_paths = [root / artifact.get("compressed_path", "") for artifact in artifacts]
    source_paths = [root / artifact.get("source_path", "") for artifact in artifacts]

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.materialized_storage_hashes_contract.v441_v450",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("training_allowed") is False,
        "compression_contract_ok": contract.get("compression", {}).get("primary_codec") == "zstd" and contract.get("compression", {}).get("compressed_extension") == ".zst",
        "cargo_binary_registered": 'name = "omnibet-materialized-storage-hasher"' in cargo and 'src/bin/omnibet-materialized-storage-hasher.rs' in cargo,
        "runner_hashes_and_compresses": "sha256_hex" in runner and "compress_zstd" in runner and "storage_hashes_verified" in runner,
        "manifest_schema_ok": manifest.get("schema") == "omnibet.materialized_storage_manifest.v441_v450",
        "manifest_required_fields_ok": required_subset(contract.get("manifest_required_fields", []), manifest),
        "manifest_safe": manifest.get("paper_only") is True and manifest.get("ready_for_training") is False and manifest.get("trust_status") == "sample_only" and manifest.get("recommendation_output_present") is False,
        "artifact_count_ok": manifest.get("artifact_count") == 8 and len(artifacts) == 8,
        "artifact_records_shape_ok": all(required_subset(record_required, artifact) for artifact in artifacts),
        "artifact_hashes_ok": all(is_sha256_hex(artifact.get("sha256", "")) and is_sha256_hex(artifact.get("compressed_sha256", "")) for artifact in artifacts),
        "artifact_paths_exist": all(path.exists() for path in source_paths) and all(path.exists() for path in compressed_paths),
        "compressed_paths_are_zst": all(str(path).endswith(".zst") for path in compressed_paths),
        "artifact_sizes_ok": all(artifact.get("source_bytes", 0) > 0 and artifact.get("compressed_bytes", 0) > 0 for artifact in artifacts),
        "artifact_status_ok": all(artifact.get("codec") == "zstd" and artifact.get("status") == "hashed_and_compressed" for artifact in artifacts),
        "verification_schema_ok": verification.get("schema") == "omnibet.materialized_storage_verification_report.v441_v450",
        "verification_matches_manifest": verification.get("run_id") == manifest.get("run_id") and verification.get("artifact_count") == manifest.get("artifact_count") and verification.get("all_hashes_present") is True and verification.get("all_compressed_copies_present") is True,
        "verification_safe": verification.get("ready_for_training") is False and verification.get("trust_status") == "sample_only" and verification.get("recommendation_output_present") is False,
        "docs_updated": "v441-v450 Materialized Storage Hashes" in docs and "ready_for_training = false" in docs and "zstd" in docs,
        "workflow_updated": "omnibet-materialized-storage-hasher" in workflow and "materialized_storage_hashes_smoke.py" in workflow and "upload-artifact" in workflow,
        "explicit_safety_flags_ok": explicit_safety_flags_ok(contract) and explicit_safety_flags_ok(manifest) and explicit_safety_flags_ok(verification),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.materialized_storage_hashes_smoke.v441_v450",
        "milestone": "v441_v450_materialized_storage_hashes_and_compression_backed_artifacts",
        "acceptance": checks,
        "summary": {
            "artifact_count": manifest.get("artifact_count"),
            "status": manifest.get("status"),
            "total_source_bytes": verification.get("total_source_bytes"),
            "total_compressed_bytes": verification.get("total_compressed_bytes"),
            "overall_compression_ratio": verification.get("overall_compression_ratio"),
            "ready_for_training": manifest.get("ready_for_training"),
            "trust_status": manifest.get("trust_status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--manifest", default="reports/materialized/v441_v450/materialized_storage_manifest.json")
    ap.add_argument("--verification", default="reports/materialized/v441_v450/materialized_storage_verification_report.json")
    ap.add_argument("--out", default="reports/ci_v441_v450_materialized_storage_hashes.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), Path(args.manifest), Path(args.verification))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
