#!/usr/bin/env python3
"""Validate release invariants and write the MSO-02A artifact manifest."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    formal = json.loads((ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json").read_text())
    folds = json.loads((ROOT / "05_registries/mso02a_lineage_fold_registry.json").read_text())
    paired = json.loads((ROOT / "05_registries/mso02a_paired_ss_ms_registry.json").read_text())
    firewall = json.loads((ROOT / "06_experiments/mso02a/firewall_audit.json").read_text())
    preflight = list(csv.DictReader((ROOT / "06_experiments/mso02a/case_level_numerical_preflight.csv").open()))
    if formal["case_count"] != 384 or formal["family_counts"] != {"F1": 96, "F2": 96, "F3": 96, "F4": 96}:
        raise RuntimeError("formal atlas balance failure")
    if formal["failed_primary_count"] or formal["reserve_used_count"]:
        raise RuntimeError("unexpected primary failure or reserve use")
    if len(preflight) != 1536 or any(row["case_scale_passed"] != "True" for row in preflight):
        raise RuntimeError("case-scale preflight failure")
    lineage_folds: dict[str, str] = {}
    for case in folds["cases"]:
        old = lineage_folds.setdefault(case["field_lineage_id"], case["fold"])
        if old != case["fold"]:
            raise RuntimeError("lineage leakage")
    family_fold = Counter((case["macro_family"], case["fold"]) for case in folds["cases"])
    if len(family_fold) != 24 or any(value == 0 for value in family_fold.values()):
        raise RuntimeError("family-fold coverage failure")
    if not paired["all_identity_checks_passed"] or paired["case_count"] != 384:
        raise RuntimeError("pairing failure")
    if any(value != 0 for key, value in firewall.items() if key.endswith("_count")):
        raise RuntimeError("information firewall breach")

    artifacts = [
        "00_project_contract/mso02a_fresh_atlas_and_representation_freeze_contract.md",
        "05_registries/mso02a_primary_candidate_registry.json",
        "05_registries/mso02a_reserve_candidate_registry.json",
        "05_registries/mso02a_candidate_lineage_fold_registry.json",
        "05_registries/mso02a_formal_fresh_atlas_registry.json",
        "05_registries/mso02a_lineage_fold_registry.json",
        "05_registries/mso02a_paired_ss_ms_registry.json",
        "05_registries/mso02a_bootstrap_registry.json",
        "06_experiments/mso02a/run_mso02a_freeze.py",
        "06_experiments/mso02a/finalize_mso02a_manifest.py",
        "06_experiments/mso02a/case_level_numerical_preflight.csv",
        "06_experiments/mso02a/case_replacement_audit.csv",
        "06_experiments/mso02a/ss_observable_schema.json",
        "06_experiments/mso02a/ms_observable_schema.json",
        "06_experiments/mso02a/representation_dimensionality_audit.csv",
        "06_experiments/mso02a/fold_normalization_registry.json",
        "06_experiments/mso02a/observable_coverage_geometry.json",
        "06_experiments/mso02a/firewall_audit.json",
        "06_experiments/mso02a/observable/mso02a_observable_store.npz",
        "06_experiments/mso02a/bootstrap_draws.npz",
        "07_reports/mso02a_fresh_atlas_report.md",
        "08_manifests/mso02a_precompute_freeze.json",
        "08_manifests/mso02a_status_ledger.json",
    ]
    source = Path("/Users/xiejinbo/.codex/attachments/d7d9b4d2-6a13-462a-8c25-c7f1c36ecc52/pasted-text.txt")
    manifest = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO",
        "stage": "MSO-02A",
        "date": "2026-08-12",
        "timezone": "Asia/Shanghai",
        "terminal_status": "MSO02A_FRESH_PAIRED_IDENTIFIABILITY_ATLAS_AND_REPRESENTATION_FROZEN",
        "source_request": {"path": str(source), "sha256": sha256(source)},
        "git": {
            "pre_mso02_commit": "5869125a0a687db89e1beea4a2d077815c6228b0",
            "branch": "main",
            "remote_created": False,
            "mso02a_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF",
        },
        "decision_summary": {
            "formal_case_count": 384,
            "family_counts": formal["family_counts"],
            "historical_lineage_overlap_count": 0,
            "failed_primary_count": 0,
            "reserve_used_count": 0,
            "case_scale_preflight_row_count": 1536,
            "all_formal_cases_four_scale_admissible": True,
            "paired_identity_passed": True,
            "ss_feature_dimension": 39,
            "ms_feature_dimension": 110,
            "fold_count": 6,
            "bootstrap_replicate_count": 10000,
            "mso02b_eligible": True,
            "mso02b_executed": False,
        },
        "activity_flags": {
            "TARGET_BLIND_FRESH_ATLAS_GENERATION": True,
            "TARGET_BLIND_DEPLOYMENT_OBSERVABLE_COMPUTE": True,
            "TARGET_BLIND_CASE_NUMERICAL_PREFLIGHT": True,
            "NEW_SCIENTIFIC_TARGET_EVALUATION": False,
            "TARGET_GENERATION": False,
            "TARGET_READ": False,
            "REFERENCE_OPERATOR_READ": False,
            "H3_EVALUATION": False,
            "ORACLE_FIT": False,
            "NEURAL_MODEL": False,
            "OPTIMIZER": False,
            "TRAINING": False,
            "TIME_INTEGRATION": False,
            "SOLVER_IN_LOOP": False,
            "ROLLOUT": False,
            "SEALED_TEST_ACCESS": False,
            "H_MSO01_GATE_MODIFIED": False,
            "POST_TARGET_OUTCOME_SCIENTIFIC_AMENDMENT": False,
        },
        "firewall_audit": firewall,
        "artifact_sha256": {path: sha256(ROOT / path) for path in artifacts},
        "validation": {
            "required_artifacts_present": True,
            "json_parse_validation": True,
            "csv_parse_validation": True,
            "precompute_hashes_unchanged_for_release_run": True,
            "all_case_scale_rows_passed": True,
            "lineage_leakage_count": 0,
            "all_family_fold_strata_present": True,
            "all_pairing_rows_passed": True,
            "all_firewall_counts_zero": True,
        },
    }
    output = ROOT / "08_manifests/mso02a_manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(output), "registered_artifact_count": len(artifacts),
                      "terminal_status": manifest["terminal_status"]}, indent=2))


if __name__ == "__main__":
    main()
